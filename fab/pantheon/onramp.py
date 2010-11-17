import os
import re
import tempfile

import pantheon
import project

from fabric.api import *

class ImportTools(project.BuildTools):

    def __init__(self, project, **kw):
        """Inherit install.InstallTools and initialize. Create addtional
        processing directory for import process.

        """
        super(ImportTools, self).__init__(project)

        self.working_dir = tempfile.mkdtemp()
        self.processing_dir = tempfile.mkdtemp()
        self.destination = os.path.join(self.server.webroot, project)
        self.author = 'Hudson User <hudson@pantheon>'
        self.db_password = pantheon.random_string(10)

    def extract(self, tarball):
        """ tarball: full path to archive to extract."""

        # Extract the archive
        archive = pantheon.PantheonArchive(tarball)
        extract_location = archive.extract()

        # Find the Drupal installation and move it to the processing_dir
        drupal_location = os.path.join(extract_location, archive.get_drupal_tld())
        local('rsync -avz %s/ %s/' % (drupal_location.rstrip('/'), self.processing_dir))
        local('rm -rf %s' % extract_location)

        # Remove existing VCS files.
        with cd(self.processing_dir):
            with settings(hide('warnings'), warn_only=True):
                local("rm -r ./.bzr")
                local("rm -r ./.git")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")

        archive.close()

    def parse_archive(self):
        """Get the site name and database dump file from archive to be imported.

        """
        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()

    def setup_project_branch(self):
        platform, version, revision = self._get_drupal_version_info()
        super(ImportTools, self).setup_project_branch(revision)

    def setup_working_dir(self):
        super(ImportTools, self).setup_working_dir(self.working_dir)

    def setup_database(self):
        """ Create a new database and import from dumpfile.

        """
        for env in self.environments:
            if env == 'dev':
                db_dump = os.path.join(self.processing_dir, self.db_dump)
            else:
                db_dump = None
            super(ImportTools, self).setup_database(env, self.db_password, db_dump)
        local('rm -f %s' % (os.path.join(self.processing_dir, self.db_dump)))

    def import_site_files(self):
        """Create git branch of project at same revision and platform of
        imported site. Import files into this branch and setup default site.

        """
        with cd(self.working_dir):
            local('git checkout pantheon')
            local('rm -rf %s/*' % self.working_dir)
            local('rsync -avz %s/* %s' % (self.processing_dir, self.working_dir))
            local('rm -f PRESSFLOW.txt')
        local('rm -rf %s' % self.processing_dir)

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
        with cd(temp_dir):
            local("drush dl -y memcache apachesolr varnish")
            local("cp -R * %s" % module_dir)
        local("rm -rf " + temp_dir)
        #TODO: Handle pantheon required modules existing in sites/default/modules.

    def setup_pantheon_libraries(self):
        super(ImportTools, self).setup_pantheon_libraries(self.working_dir)

    def setup_files_dir(self):
        file_location = self._get_files_dir()
        if file_location:
            file_path = os.path.join(self.working_dir, file_location)
        else:
            file_path = None
        file_dest = os.path.join(self.working_dir, 'sites/default/files')

        # After moving site to 'default', does 'files' not exist?
        if not os.path.exists(file_dest):
            local('mkdir -p %s' % file_dest)

            if file_path:
                # Move files to sites/default/files and symlink from former location.
                local('cp -R %s/* %s' % (file_path, file_dest))
                local('rm -rf %s' % file_path)
                path = os.path.split(file_path)
                if not os.path.islink(path[0]):
                    rel_path = os.path.relpath(file_dest, os.path.split(file_path)[0])
                    local('ln -s %s %s' % (rel_path, file_path))

        # Change paths in the files table
        database = '%s_%s' % (self.project, 'dev')
        local('mysql -u root %s -e "UPDATE files SET filepath = \
               REPLACE(filepath,\'%s\',\'%s\');"' % (database,
                                                     file_location,
                                                     'sites/default/files'))

        # Change file_directory_path drupal variable
        file_directory_path = 's:19:\\"sites/default/files\\";'
        local('mysql -u root %s -e "UPDATE variable \
                                    SET value = \'%s\' \
                                    WHERE name = \'file_directory_path\';"' % (
                                    database,
                                    file_directory_path))

        # Ignore files directory
        with open(os.path.join(file_dest,'.gitignore'), 'a') as f:
            f.write('*\n')
            f.write('!.gitignore\n')

    def enable_pantheon_settings(self):
        """Enable required modules, and set Pantheon variable defaults.

        """
        required_modules = ['apachesolr',
                            'apachesolr_search',
                            'cookie_cache_bypass',
                            'locale',
                            'syslog',
                            'varnish']
        # Solr variables
        drupal_vars = {}
        drupal_vars['apachesolr_search_make_default'] = 1
        drupal_vars['apachesolr_search_spellcheck'] = True

        # admin/settings/performance variables
        drupal_vars['cache'] = '3' # external
        drupal_vars['page_cache_max_age'] = 900
        drupal_vars['block_cache'] = True
        drupal_vars['page_compression'] = 0
        drupal_vars['preprocess_js'] = True
        drupal_vars['preprocess_css'] = True

        alias = 'working_dir'
        for module in required_modules:
            pantheon.drush(alias, 'en', module)
        with settings(warn_only=True):
            pantheon.drush_set_variables(alias, drupal_vars)

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
                 "$_SERVER['db_name'] = %s_%s;" % (self.project, 'dev'),
                 "$_SERVER['db_username'] = %s;" % self.project,
                 "$_SERVER['db_password'] = %s;" % self.db_password,
                 "$options['uri'] = 'default';",
                 "$options['root'] = '%s';" % self.working_dir]

        with open('/opt/drush/aliases/working_dir.alias.drushrc.php', 'w') as f:
            for line in lines:
                f.write(line + '\n')

    def setup_vhost(self):
        super(ImportTools, self).setup_vhost(self.db_password)

    def setup_environments(self):
        super(ImportTools, self).setup_environments('import', self.working_dir)

    def setup_permissions(self):
        super(ImportTools, self).setup_permissions('import')

    def push_to_repo(self):
        super(ImportTools, self).push_to_repo('import')

    def cleanup(self, tarball):
        """ Remove working directory and downloaded tarball.

        """
        local('rm -rf %s' % self.working_dir)
        local('rm -rf %s' % os.path.dirname(tarball))

    def _get_site_name(self):
        with cd(self.processing_dir):
            settings_files = (local('find sites/ -name settings.php -type f')).rstrip('\n')
        if not settings_files:
            abort('No settings.php files found.')
        if '\n' in settings_files:
            abort('Multiple settings.php files found.')
        name = re.search(r'^.*sites/(.*)/settings.php', settings_files).group(1)
        return name

    def _get_database_dump(self):
        with cd(self.processing_dir):
            with settings(warn_only=True):
                sql_dump = (local("find . -maxdepth 1 -type f | grep '\.sql'"
                                  )).replace('./','').rstrip('\n')
                if not sql_dump:
                    abort("No .sql files found")
        if '\n' in sql_dump:
            abort('Multiple database dumps found.')
        return sql_dump

    def _get_drupal_version_info(self):
        platform = self._get_drupal_platform()
        version = self._get_drupal_version()
        if platform == 'DRUPAL':
            revision = 'DRUPAL-%s' % version
        elif platform == 'PRESSFLOW':
            revision = self._get_pressflow_revision()
        return (platform, version, revision)

    def _get_drupal_platform(self):
        return ((local("awk \"/\'info\' =>/\" " + \
                self.processing_dir + \
                "/modules/system/system.module" + \
                r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')
                ).rstrip('\n').upper())

    def _get_drupal_version(self):
        return ((local("awk \"/define\(\'VERSION\'/\" " + \
                self.processing_dir + "/modules/system/system.module" + \
                "| sed \"s_^.*'\(6\)\.\([0-9]\{1,2\}\)'.*_\\1-\\2_\"")
                ).rstrip('\n'))

    def _get_pressflow_revision(self):
        #TODO: Optimize this (restrict search to revisions within Drupal minor version)
        temporary_directory = tempfile.mkdtemp()
        local("git clone git://gitorious.org/pantheon/6.git " + temporary_directory)
        with cd(temporary_directory):
            match = {'difference': None, 'commit': None}
            commits = local("git log | grep '^commit' | sed 's/^commit //'").split('\n')
            print "\nPlease Wait. Determining closest Pantheon revision.\n" + \
                  "This could take a few minutes.\n"
            for commit in commits:
                if len(commit) > 1:
                    with hide('running'):
                        local("git reset --hard " + commit)
                        difference = int(local("diff -rup " + self.processing_dir + " ./ | wc -l"))
                        # print("Commit " + commit + " shows difference of " + str(difference))
                        if match['commit'] == None or difference < match['difference']:
                            match['difference'] = difference
                            match['commit'] = commit
        local('rm -rf %s' % temporary_directory)
        return match['commit']

    def _get_files_dir(self, env='dev'):
        database = '%s_%s' % (self.project, env)
        # Get file_directory_path directly from database, as we don't have a working drush yet.
        return local("mysql -u %s -p'%s' %s --skip-column-names --batch -e \
                      \"SELECT value FROM variable WHERE name='file_directory_path';\" | \
                        sed 's/^.*\"\(.*\)\".*$/\\1/'" % (self.project,
                                                          self.db_password,
                                                          database)).rstrip('\n')

