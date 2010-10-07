import os
import re
import tempfile

from fabric.api import *

import install
import pantheon

def download(url):
    """Download url to temporary directory and return path to file.
    url: fully qualified url of file to download.
    returns: full path to downloaded file.

    """
    download_dir = tempfile.mkdtemp()
    filebase = os.path.basename(url)
    filename = os.path.join(download_dir, filebase)

    _curl(url, filename)
    return filename


def drush(alias, cmd, option):
    """Use drush to run a command on an aliased site.
    alias: alias name of site (just name, no '@')
    cmd: drush command to run
    option: options / parameters for the command.

    """
    with settings(warn_only=True):
        local('drush -y @%s %s %s' % (alias, cmd, option))
   

def drush_set_variables(alias, variables = dict()):
    """Set drupal variables using drush. php-eval is used because drush vset 
    always sets vars as strings.
    alias: alias name of site (just name, no '@')
    variables: dict of var_name/values.

    """
    for key, value in variables.iteritems():
        # normalize strings and bools
        if isinstance(value, str):
            value = "'%s'" % value
        if isinstance(value, bool):
            if value == True:
                value = 'TRUE'
            elif value == False:
                value = 'FALSE'
        local("drush @%s php-eval \"variable_set('%s',%s);\"" % (alias, 
                                                                key, 
                                                                value))


def _curl(url, destination):
    """Use curl to save url to destination.
    url: url to download
    destination: full path/ filename to save curl output.

    """
    local('curl "%s" -o "%s"' % (url, destination)) 


class ImportTools(install.InstallTools):


    def __init__(self, project):
        """Inherit install.InstallTools and initialize. Create addtional
        processing directory for import process.

        """
        install.InstallTools.__init__(self, project)
        self.processing_dir = tempfile.mkdtemp()


    def extract(self, tarball):
        """Use bzr import to extract archive. bzr import is used for this
        because it can handle zero or one top level directories, and supports
        .tar.gz/.tar/.gz/.zip archives. After extraction remove all VCS files
        (including bzr/git/cvs/svn)
        tarball: full path to archive to extract.

        """
        local('bzr init %s' % self.processing_dir)
        with cd(self.processing_dir):
            local("bzr import %s" % tarball)
            with settings(hide('warnings'), warn_only=True):
                local("rm -r ./.bzr")
                local("rm -r ./.git")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")

        local('rm -rf %s' % os.path.dirname(tarball))


    def parse_archive(self):
        """Get the site name and database dump file from archive to be imported.

        """
        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()


    def import_database(self, environments=pantheon.get_environments()):
        """ Create a new database and set user grants (all), then import
        using 'project_dev' as the name.

        """
        username = self.project
        password = self.db_password

        for env in environments:
            database = '%s_%s' % (self.project, env)
            local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
            local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS %s'" % (database))
            local("mysql -u root -e \"GRANT ALL ON %s.* TO '%s'@'localhost' \
                                      IDENTIFIED BY '%s';\"" % (database,
                                                                username,
                                                                password))        

        # Strip cache tables, convert MyISAM to InnoDB, and import into dev.
        local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | \
               grep -v '^INSERT INTO `ctools_object_cache`' | \
               grep -v '^INSERT INTO `watchdog`' | \
               grep -v '^INSERT INTO `accesslog`' | \
               grep -v '^USE `' | \
               sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | \
               mysql -u root %s" %  (os.path.join(self.processing_dir,
                                     self.db_dump), 
                                     database))
        local('rm -f %s' % (os.path.join(self.processing_dir, self.db_dump)))
   
 
    def import_files(self):
        """Create git branch of project at same revision and platform of 
        imported site. Import files into this branch and setup default site.
        
        """
        #TODO: add large file size sanity check (no commits over 20mb)
        platform, version, revision = self._get_drupal_version_info()

        with cd('/var/git/projects/%s' % self.project):
            if platform == 'PRESSFLOW':
                local('git checkout master')
                local('git pull')
            elif platform == 'DRUPAL':
                local('git checkout drupal_core')
                local('git pull git://gitorious.org/drupal/6.git')
            with settings(hide('warnings'), warn_only=True):
                local('git tag -d %s.import' % self.project)
                local('git branch -D %s' % self.project)
            local('git branch %s %s' % (self.project, revision))
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project, 
                                                              self.project, 
                                                              self.working_dir))
        with cd(self.working_dir):
            local('git checkout pantheon')
            local('rm -rf %s/*' % self.working_dir)
            local('rsync -avz %s/* %s' % (self.processing_dir, self.working_dir))
            local('rm -f PRESSFLOW.txt')
        local('rm -rf %s' % self.processing_dir)

        #Standardize on sites/default.
        self._setup_default_site()
        self._setup_default_files()


    def import_pantheon_modules(self):
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
    
        # Download SolrPhpClient library
        with cd(os.path.join(module_dir, 'apachesolr')):
            local("wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz")
            local("tar xzf SolrPhpClient.r22.2009-11-09.tgz")
            local("rm SolrPhpClient.r22.2009-11-09.tgz")

        site_module_dir = os.path.join(self.working_dir, 'sites/%s/modules' % self.site)
        if os.path.exists(site_module_dir):
            with cd(site_module_dir):
                if os.path.exists("apachesolr"):
                    local("drush dl -y apachesolr")
                if os.path.exists("memcache"):
                    local("drush dl -y memcache")
                if os.path.exists("varnish"):
                    local("drush dl -y varnish")

 
    def import_drupal_settings(self):
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

        alias = '%s_%s' % (self.project, 'dev')
        for module in required_modules:
            drush(alias, 'en', module)
        with settings(warn_only=True):
            drush_set_variables(alias, drupal_vars)


    def setup_permissions(self, environments=pantheon.get_environments()):
        """ Set permissions on project directory, settings.php, and files dir.
        environments: Optional. List.

        """
        with cd(self.server.webroot):
            local('chown -R root:%s %s' % (self.server.web_group, self.project))
        file_dir = self._get_files_dir()
        for env in environments:
            site_dir = os.path.join(self.server.webroot, \
                                    '%s/%s/sites/default' % (self.project, env))
            with cd(site_dir):
                local('chown %s:%s settings.php' % ('root',
                                                    self.server.web_group))
                local('chmod 440 settings.php')
                local('chmod 440 pantheon.settings.php')
            file_path = os.path.join(self.server.webroot, '%s/%s/%s' % (
                                           self.project, env, file_dir))
            with cd(file_path): 
                local("chmod 770 .")
                local("find . -type d -exec find '{}' -type f \; | \
                       while read FILE; do chmod 660 \"$FILE\"; done")
                local("find . -type d -exec find '{}' -type d \; | \
                      while read DIR; do chmod 770 \"$DIR\"; done")


    def update_environment_databases(self, environments=pantheon.get_environments()):
        tempdir = tempfile.mkdtemp()
        dump_file = pantheon.export_data(self.project, 'dev', tempdir)
        for env in environments:
            if env != 'dev':
                pantheon.import_data(self.project, env, dump_file)
        local('rm -rf %s' % tempdir)


    def update_environment_files(self, environments=pantheon.get_environments()):
        source = os.path.join(self.working_dir, 'sites/default/files')
        for env in environments:
            destination = os.path.join(self.server.webroot, 
                          '%s/%s/sites/default/' % (self.project, env))
            local('rsync -av %s %s' % (source, destination))


    def _setup_default_site(self):
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


        # Setup settings.php and pantheon.settings.php
        pantheon.create_pantheon_settings_file(destination)

                   
    def _setup_default_files(self):
        file_location = self._get_files_dir()
        file_path = os.path.join(self.working_dir, file_location)
        file_dest = os.path.join(self.working_dir, 'sites/default/files')

        if not os.path.exists(file_dest):
            local('mkdir -p %s' % file_dest)

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
        

    def _get_site_name(self):
        with cd(self.processing_dir):
            settings_files = (local('find sites/ -name settings.php -type f')).rstrip('\n')
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
        return ((local("awk \"/\'info\' =>/\" " + self.processing_dir + "/modules/system/system.module" + \
                r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')).rstrip('\n').upper())


    def _get_drupal_version(self):
        return ((local("awk \"/define\(\'VERSION\'/\" " + self.processing_dir + "/modules/system/system.module" + \
                "| sed \"s_^.*'\(6\)\.\([0-9]\{1,2\}\)'.*_\\1-\\2_\"")).rstrip('\n'))


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
        
