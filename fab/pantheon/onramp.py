import os
import tempfile

import dbtools
import drupaltools
import hudsontools
import pantheon
import project
import postback

from fabric.api import *

def get_drupal_root(base):
    """Return the location of drupal root within 'base' dir tree.

    """
    for root, dirs, files in os.walk(base, topdown=True):
        if ('index.php' in files) and ('sites' in dirs):
            hudsontools.junit_pass('Drupal root found.', 'DrupalRoot')
            return root
    err = 'Cannot locate drupal install in archive.'
    hudsontools.junit_fail(err, 'DrupalRoot')
    postback.build_error(err)

def download(url):
    if url.startswith('file:///'):
        # Local file - return path
        return url[7:]
    else:
        # Download remote file into temp location with known prefix.
        return pantheon.download(url, 'tmp_dl_')

def extract(tarball):
    """ tarball: full path to archive to extract."""

    # Extract the archive
    archive = pantheon.PantheonArchive(tarball)
    extract_location = archive.extract()
    archive.close()

    # In the case of very large sites, people will manually upload the
    # tarball to the machine. In these cases, we don't want to remove this
    # file. However if the import script downloaded the file from a remote
    # location, go ahead and remove it at the end of processing.
    archive_location = os.path.dirname(tarball)
    # Downloaded by import script (known location), remove after extract.
    if archive_location.startswith('/tmp/tmp_dl_'):
        local('rm -rf %s' % archive_location)

    return extract_location

def get_onramp_profile(base):
    """Determine what onramp profile to use (import or restore)

    """
    #TODO: make this more efficient. Could walk through a huge import.
    for root, dirs, files in os.walk(base, topdown=True):
        if ('pantheon.backup' in files) and ('live' in dirs):
            # Restore if a backup config file and a live folder exists.
            return 'restore'
    # Otherwise run the import profile.
    return 'import'


class ImportTools(project.BuildTools):

    def __init__(self, project):
        """Inherit install.InstallTools and initialize. Create addtional
        processing directory for import process.

        """
        super(ImportTools, self).__init__(project)

        self.destination = os.path.join(self.server.webroot, project)
        self.author = 'Hudson User <hudson@pantheon>'
        self.db_password = pantheon.random_string(10)
        self.force_update = False

    def parse_archive(self, extract_location):
        """Get the site name and database dump file from archive to be imported.

        """
        # Find the Drupal installation and set it as the working_dir
        self.working_dir = get_drupal_root(extract_location)

        # Remove existing VCS files.
        with cd(self.working_dir):
            with settings(hide('warnings'), warn_only=True):
                local("rm -r ./.bzr")
                local("rm -r ./.git")
                local("find . -depth -name '._*' -exec rm -fr {} \;")
                local("find . -depth -name .git -exec rm -fr {} \;")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")

        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()
        self.version, self.revision = self._get_drupal_version_info()

    def setup_project_branch(self):
        # Pressflow branches at 6.6. If on an earlier version, force update.
        if self.revision in ['DRUPAL-6-%s' % i for i in range(6)]:
            self.revision = 'DRUPAL-6-6'
            self.force_update = True
        super(ImportTools, self).setup_project_branch(self.revision)

    def setup_database(self):
        """ Create a new database and import from dumpfile.

        """
        for env in self.environments:
            # The database is only imported into the dev environment initially
            # so that we can do all import processing in one place, then deploy
            # to the other environments.
            if env == 'dev':
                db_dump = os.path.join(self.working_dir, self.db_dump)
            else:
                db_dump = None

            super(ImportTools, self).setup_database(env,
                                                    self.db_password,
                                                    db_dump,
                                                    True)
        # Remove the database dump from processing dir after import.
        local('rm -f %s' % (os.path.join(self.working_dir, self.db_dump)))

    def import_site_files(self):
        """Create git branch of project at same revision and platform of
        imported site. Import files into this branch and setup default site.

        """
        # Get git metadata at correct branch/version point.
        temp_dir = tempfile.mkdtemp()
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              temp_dir))
        # Put the .git metadata on top of imported site.
        with cd(temp_dir):
            local('git checkout pantheon')
            local('cp -R .git %s' % self.working_dir)
        with cd(self.working_dir):
            local('rm -f PRESSFLOW.txt')
            # If drupal version is prior to 6.6 (when pressflow was forked),
            # force an upgrade to 6.6 (so later operations are supported).
            if self.force_update:
                local('git reset --hard')
        local('rm -rf %s' % temp_dir)

        source = os.path.join(self.working_dir, 'sites/%s' % self.site)
        destination = os.path.join(self.working_dir, 'sites/default')

        # Move sites/site_dir to sites/default
        if self.site != 'default':
            if os.path.exists(destination):
                local('rm -rf %s' % destination)
            local('mv %s %s' % (source, destination))
            # Symlink site_dir to default
            with cd(os.path.join(self.working_dir,'sites')):
                local('ln -s %s %s' % ('default', self.site))

    def setup_pantheon_modules(self):
        """Setup required Pantheon modules and libraries.

        """
        module_dir = os.path.join(self.working_dir, 'sites/all/modules')
        if not os.path.exists(module_dir):
            local('mkdir -p %s' % module_dir)

        # Download modules in temp dir so drush doesn't complain.
        temp_dir = tempfile.mkdtemp()
        if self.version == 6:
            modules = ['apachesolr','memcache','varnish']
        else:
            modules = ['apachesolr-7.x-1.0-beta3', 'memcache-7.x-1.0-beta3']
        with cd(temp_dir):
            local("drush dl -y %s" % ' '.join(modules))
            local("cp -R * %s" % module_dir)
        local("rm -rf " + temp_dir)
        #TODO: Handle pantheon required modules existing in sites/default/modules.

    def setup_pantheon_libraries(self):
        super(ImportTools, self).setup_pantheon_libraries(self.working_dir)

    def setup_files_dir(self):
        """Move site files to sites/default/files if they are not already.

        This will move the files from their former location, change the file
        path in the database (for all files and the variable itself), then
        create a symlink in their former location.

        """
        file_location = self._get_files_dir()
        if file_location:
            file_path = os.path.join(self.working_dir, file_location)
        else:
            file_path = None
        file_dest = os.path.join(self.working_dir, 'sites/default/files')

        # After moving site to 'default', does 'files' not exist?
        if not os.path.exists(file_dest):
            # Broken symlink at sites/default/files
            if os.path.islink(file_dest):
                local('rm -f %s' % file_dest)
                msg = 'File path was broken symlink. Site files may be missing'
                hudsontools.junit_fail(msg, 'SetupFilesDir')
                postback.build_warning(msg)
            local('mkdir -p %s' % file_dest)

        # if files are not located in default location, move them there.
        if (file_path) and (file_location != 'sites/default/files'):
            with settings(warn_only=True):
                local('cp -R %s/* %s' % (file_path, file_dest))
            local('rm -rf %s' % file_path)
            path = os.path.split(file_path)
            # Symlink from former location to sites/default/files
            if not os.path.islink(path[0]):
                rel_path = os.path.relpath(file_dest, os.path.split(file_path)[0])
                local('ln -s %s %s' % (rel_path, file_path))

        # Change paths in the files table
        database = '%s_%s' % (self.project, 'dev')

        if self.version == 6:
            file_var = 'file_directory_path'
            file_var_temp = 'file_directory_temp'
            # Change the base path in files table for Drupal 6
            local('mysql -u root %s -e "UPDATE files SET filepath = \
                   REPLACE(filepath,\'%s\',\'%s\');"'% (database,
                                                        file_location,
                                                        'sites/default/files'))
        elif self.version == 7:
            file_var = 'file_public_path'
            file_var_temp = 'file_temporary_path'

        # Change file path drupal variables
        db = dbtools.MySQLConn(database=database,
                               username = self.project,
                               password = self.db_password)
        db.vset(file_var, 'sites/default/files')
        db.vset(file_var_temp, '/tmp')
        db.close()

        # Ignore files directory
        with open(os.path.join(file_dest,'.gitignore'), 'a') as f:
            f.write('*\n')
            f.write('!.gitignore\n')

    def enable_pantheon_settings(self):
        """Enable required modules, and set Pantheon defaults.

        """
        if self.version == 6:
            required_modules = ['apachesolr',
                                'apachesolr_search',
                                'cookie_cache_bypass',
                                'locale',
                                'syslog',
                                'varnish']
        elif self.version == 7:
            required_modules = ['apachesolr',
                                'apachesolr_search']

        # Enable modules.
        with settings(hide('warnings'), warn_only=True):
            for module in required_modules:
                result = local('drush -y @working_dir en %s' % module)
                if result.failed:
                    # If importing vanilla drupal, this module wont exist.
                    if module != 'cookie_cache_bypass':
                        message = 'Could not enable %s module.' % module
                        hudsontools.junit_fail('%s\n%s' % 
                                               (message, result.stderr), 
                                               'EnableModules', module)
                        postback.build_warning(message)
                        print message
                        print '\n%s module could not be enabled. ' % module + \
                              'Error Message:'
                        print '\n%s' % result.stderr
                else:
                    hudsontools.junit_pass('%s enabled.' % module, 
                                           'EnableModules', module)

        if self.version == 6:
            drupal_vars = {
                'apachesolr_search_make_default': 1,
                'apachesolr_search_spellcheck': 1,
                'cache': '3',
                'block_cache': '1',
                'page_cache_max_age': '900',
                'page_compression': '0',
                'preprocess_js': '1',
                'preprocess_css': '1'}

        elif self.version == 7:
            drupal_vars = {
                'cache': 1,
                'block_cache': 1,
                'cache_lifetime': "0",
                'page_cache_maximum_age': "900",
                'page_compression': 0,
                'preprocess_css': 1,
                'preprocess_js': 1,
                'search_active_modules': {
                    'apachesolr_search':'apachesolr_search',
                    'user': 'user',
                    'node': 0},
                'search_default_module': 'apachesolr_search'}

        # Set variables.
        database = '%s_dev' % self.project
        db = dbtools.MySQLConn(database=database,
                               username = self.project,
                               password = self.db_password)
        for key, value in drupal_vars.iteritems():
            db.vset(key, value)

        # apachesolr module for drupal 7 stores config in db.
        if self.version == 7:
            db.execute('TRUNCATE apachesolr_server')
            for env in self.environments:
                db.execute('INSERT INTO apachesolr_server ' + \
                    '(host, port, server_id, name, path) VALUES ' + \
                    '("localhost", "8983", ' + \
                      '"pantheon_%s", "Pantheon %s", "/pantheon_%s")' %\
                      (env, env, env))
        db.close()

        # D7: apachesolr config link will not display until cache cleared?
        with settings(warn_only=True):
            local('drush @working_dir -y cc all')

       # Remove temporary working_dir drush alias.
        alias_file = '/opt/drush/aliases/working_dir.alias.drushrc.php'
        if os.path.exists(alias_file):
            local('rm -f %s' % alias_file)

    def setup_settings_file(self):
        site_dir = os.path.join(self.working_dir, 'sites/default')
        super(ImportTools, self).setup_settings_file(site_dir)

    def setup_drush_alias(self):
        super(ImportTools, self).setup_drush_alias()

        # Create a temporary drush alias for the working_dir.
        # It will be removed after enable_pantheon_settings() finishes.
        lines = ["<?php",
                 "$_SERVER['db_name'] = '%s_%s';" % (self.project, 'dev'),
                 "$_SERVER['db_username'] = '%s';" % self.project,
                 "$_SERVER['db_password'] = '%s';" % self.db_password,
                 "$options['uri'] = 'default';",
                 "$options['root'] = '%s';" % self.working_dir]

        with open('/opt/drush/aliases/working_dir.alias.drushrc.php', 'w') as f:
            for line in lines:
                f.write(line + '\n')

    def setup_vhost(self):
        super(ImportTools, self).setup_vhost(self.db_password)

    def setup_phpmyadmin(self):
        super(ImportTools, self).setup_phpmyadmin(self.db_password)

    def setup_environments(self):
        super(ImportTools, self).setup_environments('import', self.working_dir)

    def setup_permissions(self):
        super(ImportTools, self).setup_permissions('import')

    def push_to_repo(self):
        super(ImportTools, self).push_to_repo('import')

    def cleanup(self):
        """ Remove leftover temporary import files..

        """
        local('rm -rf %s' % self.working_dir)

    def _get_site_name(self):
        """Return the name of the site to be imported.

        A valid site is any directory under sites/ that contains a settings.php

        """
        root = os.path.join(self.working_dir, 'sites')
        sites =[s for s in os.listdir(root) \
                        if os.path.isdir(os.path.join(root,s)) and (
                           'settings.php' in os.listdir(os.path.join(root,s)))]

        # Unless only one site is found, post error and exit.  
        site_count = len(sites)
        if site_count > 1:
            err = 'Multiple settings.php files were found:\n' + \
                  '\n'.join(sites)
            hudsontools.junit_fail(err, 'SiteCount')
            postback.build_error(err)
        elif site_count == 0:
            err = 'Error: No settings.php files were found.'
            hudsontools.junit_fail(err, 'SiteCount')
            postback.build_error(err)
        else:
            hudsontools.junit_pass('Site found.', 'SiteCount')
            return sites[0]

    def _get_database_dump(self):
        """Return the filename of the database dump.

        This will look for *.mysql or *.sql files in the root drupal directory.
        If more than one dump is found, the build will exit with an error.

        """
        sql_dump = [dump for dump in os.listdir(self.working_dir) \
                    if os.path.splitext(dump)[1] in ['.sql', '.mysql']]
        count = len(sql_dump)
        if count == 0:
            err = 'No database dump files were found (*.mysql or *.sql)'
            hudsontools.junit_fail(err, 'MYSQLCount')
            postback.build_error(err)
        elif count > 1:
            err = 'Multiple database dump files were found:\n' + \
                  '\n'.join(sql_dump)
            hudsontools.junit_fail(err, 'MYSQLCount')
            postback.build_error(err)
        else:
            hudsontools.junit_pass('MYSQL Dump found at %s' %
                                   (sql_dump[0]), 'MYSQLCount')
            return sql_dump[0]

    def _get_drupal_version_info(self):
        """Determine the platform, version, and revision of the imported site.
        Returns tuple of major_version (6 or 7) and the nearest git revision.

        """
        version = drupaltools.get_drupal_version(self.working_dir)
        if not version:
            err = 'Error: This does not appear to be a Drupal 6 site.'
            hudsontools.junit_fail(err, 'DrupalVersion')
            postback.build_error(err)
        else:
            hudsontools.junit_pass('Drupal version %s found.' % (version),
                                   'DrupalVersion')

        platform = drupaltools.get_drupal_platform(self.working_dir)

        major_version = int(version[0:1])
        if major_version == 6:
            if platform == 'DRUPAL':
                revision = 'DRUPAL-%s' % version
            elif platform == 'PRESSFLOW' or platform == 'PANTHEON':
                revision = self._get_pressflow_revision(6)
        elif major_version == 7:
            #TODO: Temporary until D7 git setup is finalized.
            if platform == 'DRUPAL':
                # TODO: replace - with . in tags once git repo is finalized.
                revision = version.replace('-','.') # temp hack
            elif platform == 'PRESSFLOW' or platform == 'PANTHEON':
                revision = self._get_pressflow_revision(7)
        return (major_version, revision)

    def _get_pressflow_revision(self, version=6):
        #TODO: Make sure this is D7 friendly once Pressflow setup is finalized.
        print "\nPlease Wait. Determining closest Pantheon revision.\n"
        temp_dir = tempfile.mkdtemp()
        repo = 'git://git.getpantheon.com/pantheon/%s.git' % version
        local('git clone %s %s' % (repo, temp_dir))
        with cd(temp_dir):
            match = {'diff': None, 'commit': None}
            commits = local('git log --pretty=format:%H').split('\n')
            with hide('running'):
                for commit in commits:
                    local("git reset --hard " + commit)
                    diff = int(local("diff -rup %s ./ | wc -l" % \
                                                   self.working_dir))
                    if match['commit'] == None or diff < match['diff']:
                        match['diff'] = diff
                        match['commit'] = commit
        local('rm -rf %s' % temp_dir)
        return match['commit']

    def _get_files_dir(self, env='dev'):
        database = '%s_%s' % (self.project, env)
        # Get file_directory_path directly from database, as we don't have a working drush yet.
        return local("mysql -u %s -p'%s' %s --skip-column-names --batch -e \
                      \"SELECT value FROM variable WHERE name='file_directory_path';\" | \
                        sed 's/^.*\"\(.*\)\".*$/\\1/'" % (self.project,
                                                          self.db_password,
                                                          database)).rstrip('\n')

