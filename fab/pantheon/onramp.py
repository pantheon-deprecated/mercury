import os
import tempfile

import dbtools
import drupaltools
import pantheon
import project
import postback
import logger

from fabric.api import *
#TODO: Improve the logging messages

def get_drupal_root(base):
    """Return the location of drupal root within 'base' dir tree.

    """
    log = logger.logging.getLogger('pantheon.onramp.drupalroot')
    for root, dirs, files in os.walk(base, topdown=True):
        if ('index.php' in files) and ('sites' in dirs):
            log.info('Drupal root found.')
            return root
    log.error('Cannot locate drupal install in archive.')
    postback.build_error('Cannot locate drupal install in archive.')

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
        self.log = logger.logging.getLogger('pantheon.onramp.ImportTools')
        super(ImportTools, self).__init__()

        self.author = 'Jenkins User <jenkins@pantheon>'
        self.destination = os.path.join(self.server.webroot, self.project)
        self.force_update = False

    def parse_archive(self, extract_location):
        """Get the site name and database dump file from archive to be imported.

        """
        # Find the Drupal installation and set it as the working_dir
        self.working_dir = get_drupal_root(extract_location)

        # Remove existing VCS files.
        with cd(self.working_dir):
            with settings(hide('warnings'), warn_only=True):
                local("find . -depth -name '._*' -exec rm -fr {} \;")
                local("find . -depth -name .git -exec rm -fr {} \;")
                local("find . -depth -name .bzr -exec rm -fr {} \;")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")
                # Comment any RewriteBase directives in .htaccess
                local("sed -i 's/^[^#]*RewriteBase/# RewriteBase/' .htaccess")

        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()
        self.version = int(drupaltools.get_drupal_version(self.working_dir)[0])

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
            local('git checkout %s' % self.project)
            local('cp -R .git %s' % self.working_dir)
        with cd(self.working_dir):
            local('rm -f PRESSFLOW.txt')
            # Stomp on any changes to core.
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
                self.log.info(msg)
                postback.build_warning(msg)
            local('mkdir -p %s' % file_dest)

        # if files are not located in default location, move them there.
        if (file_path) and (file_location != 'sites/%s/files' % self.site):
            with settings(warn_only=True):
                local('cp -R %s/* %s' % (file_path, file_dest))
            local('rm -rf %s' % file_path)
            path = os.path.split(file_path)
            # Symlink from former location to sites/default/files
            if not os.path.islink(path[0]):
                # If parent folder for files path doesn't exist, create it.
                if not os.path.exists(path[0]):
                    local('mkdir -p %s' % path[0])
                rel_path = os.path.relpath(file_dest, path[0])
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
                                'locale',
                                'pantheon',
                                'syslog',
                                'varnish']
        elif self.version == 7:
            required_modules = ['apachesolr',
                                'apachesolr_search',
                                'syslog']

        # Enable modules.
        with settings(hide('warnings'), warn_only=True):
            for module in required_modules:
                result = local('drush -by @working_dir en %s' % module)
                pantheon.log_drush_backend(result, self.log)
                if result.failed:
                    # If importing vanilla drupal, this module wont exist.
                    if module != 'cookie_cache_bypass':
                        message = 'Could not enable %s module.' % module
                        self.log.warning('%s\n%s' % (message, result.stderr))
                        postback.build_warning(message)
                        print message
                        print '\n%s module could not be enabled. ' % module + \
                              'Error Message:'
                        print '\n%s' % result.stderr
                else:
                    self.log.info('%s enabled.' % module)

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
        # TODO: use drush/drupal api to do this work.
        try:
            if self.version == 7:
                db.execute('TRUNCATE apachesolr_environment')
                for env in self.environments:
                    config = self.config['environments'][env]['solr']

                    env_id = '%s_%s' % (self.project, env)
                    name = '%s %s' % (self.project, env)
                    url = 'http://%s:%s%s' % (config['solr_host'],
                                              config['solr_port'],
                                              config['solr_path'])

                    # Populate the solr environments
                    db.execute('INSERT INTO apachesolr_environment ' + \
                        '(env_id, name, url) VALUES ' + \
                        '("%s", "%s", "%s")' % (env_id, name, url))

                    # Populate the solr environment variables
                    db.execute('INSERT INTO apachesolr_environment_variable '+\
                               '(env_id, name, value) VALUES ' + \
                               "('%s','apachesolr_read_only','s:1:\"0\"')" % (
                                                                      env_id))

        except Exception as mysql_error:
             self.log.error('Auto-configuration of ApacheSolr module failed: %s' % mysql_error)
             pass

        db.close()

        # D7: apachesolr config link will not display until cache cleared?
        with settings(warn_only=True):
            result = local('drush @working_dir -y cc all')
            pantheon.log_drush_backend(result, self.log)

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
        local('rm -rf %s' % self.build_location)

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
            self.log.error(err)
            postback.build_error(err)
        elif site_count == 0:
            err = 'Error: No settings.php files were found.'
            self.log.error(err)
            postback.build_error(err)
        else:
            self.log.info('Site found.')
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
            self.log.error(err)
            postback.build_error(err)
        elif count > 1:
            err = 'Multiple database dump files were found:\n' + \
                  '\n'.join(sql_dump)
            self.log.error(err)
            postback.build_error(err)
        else:
            self.log.info('MYSQL Dump found at %s' % sql_dump[0])
            return sql_dump[0]

    def _get_files_dir(self, env='dev'):
        database = '%s_%s' % (self.project, env)
        # Get file_directory_path directly from database, as we don't have a working drush yet.
        return local("mysql -u %s -p'%s' %s --skip-column-names --batch -e \
                      \"SELECT value FROM variable WHERE name='file_directory_path';\" | \
                        sed 's/^.*\"\(.*\)\".*$/\\1/'" % (self.project,
                                                          self.db_password,
                                                          database)).rstrip('\n')

