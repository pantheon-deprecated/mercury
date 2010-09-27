import os
import re
import tempfile

from fabric.api import *

import drupal
import install
import pantheon

def download(url):
    download_dir = tempfile.mkdtemp()
    filebase = os.path.basename(url)
    filename = os.path.join(download_dir, filebase)

    _curl(url, filename)
    return filename


def drush(alias, cmd, option):
    local('drush -y @%s %s %s' % (alias, cmd, option))
   

def drush_set_variables(alias, variables = dict()):
    for key, value in variables.iteritems():
        # normalize strings and bools
        if isinstance(value, str):
            value = "'" + value + "'"
        if isinstance(value, bool):
            if value == True:
                value = 'TRUE'
            elif value == False:
                value = 'FALSE'
        local("drush %s php-eval \"variable_set('%s',%s);\"" % (alias, 
                                                                key, 
                                                                value))

def _curl(url, destination):
    local('curl "%s" -o "%s"' % (url, destination)) 


class ImportTools(install.InstallTools):


    def __init__(self, project):
        install.InstallTools.__init__(self, project)
        self.processing_dir = tempfile.mkdtemp()


    def extract(self, tarball):
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
        self.site = self._get_site_name()
        self.db_dump = self._get_database_dump()


    def import_database(self, environments=pantheon.get_environments()):
        """ Create a new database and set user grants (all).

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
            if env == 'dev':
                # Strip cache tables, convert MyISAM to InnoDB, and import.
                local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | \
                       grep -v '^INSERT INTO `ctools_object_cache`' | \
                       grep -v '^INSERT INTO `watchdog`' | \
                       grep -v '^INSERT INTO `accesslog`' | \
                       grep -v '^USE `' | \
                       sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | \
                       mysql -u root %s" %  (os.path.join(self.processing_dir,
                                             self.db_dump), 
                                             database))
                local('rm -f %s' % (os.path.join(self.processing_dir, 
                                                 self.db_dump)))
   
 
    def import_files(self):
        #TODO: add large file size sanity check (no commits over 20mb)
        repo = self.working_dir
        platform, version, revision = self._get_drupal_version_info()

        with cd('/var/git/projects'):
            if platform == 'PRESSFLOW':
                local('git checkout master')
                local('git pull')
            else:
                local('git checkout drupal_core')
                local('git pull git://gitorious.org/drupal/6.git')
            with settings(hide('warnings'), warn_only=True):
                local('git tag -d %s.import' % self.project)
                local('git branch -D %s' % self.project)
            local('git branch %s %s' % (self.project, revision))
        local('git clone -l /var/git/projects -b %s %s' % (self.project, repo))
        with cd(repo):
            local('git checkout pantheon')
            local('rm -rf %s/*' % repo)
            local('rsync -avz %s/* %s' % (self.processing_dir, repo))
            local('rm -f PRESSFLOW.txt')
        self._setup_default_site()


    def import_pantheon_modules(self):
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

 
    def import_drupal_settings(self, environments=pantheon.get_environments()):
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

        for env in environments:
            alias = '%s_%s' % (self.project, env)
            for module in required_modules:
                drush(alias, 'enable', module)
            with settings(warn_only=True):
                drush_set_variables(alias, drupal_vars)


    def setup_permissions(self, environments=pantheon.get_environments()):
        """ Set permissions on project directory, settings.php, and files dir.
        environments: Optional. List.

        """
        with cd(self.server.webroot):
            local('chown -R root:%s %s' % (self.server.web_group, self.project))

        for env in environments:
            import pdb
            pdb.set_trace()
            site_dir = os.path.join(self.server.webroot, \
                                    '%s/%s/sites/default' % (self.project, env))
            with cd(site_dir):
                local('chown %s:%s settings.php' % ('root',
                                                    self.server.web_group))
                local('chmod 440 settings.php')
                local('chmod 440 pantheon.settings.php')
            file_dir = self._get_files_dir(env)
            file_path = os.path.join(self.server.webroot, '%s/%s/%s' % (self.project, env, file_dir))
            with cd(file_path): 
                local("chmod 770 .")
                local("find . -type d -exec find '{}' -type f \; | \
                       while read FILE; do chmod 660 \"$FILE\"; done")
                local("find . -type d -exec find '{}' -type d \; | \
                      while read DIR; do chmod 770 \"$DIR\"; done")


    def _setup_default_site(self):
        #TODO: Handle file paths that are not sites/sitename/files
        #TODO: Handle gitignore 
        file_dir = self._get_files_dir()
        if not file_dir:
            #TODO: Handle no file_dir set.
            pass
        destination = os.path.join(self.working_dir, 'sites/default')
        if self.site == 'default':
            pass
        else:
            source = os.path.join(self.working_dir, 'sites/%s' % self.site)
            if os.path.exists(destination):
                local('rm -rf %s' % destination)
            local('mv %s %s' % (source, destination))
            with cd(os.path.join(self.working_dir,'sites')):
                local('ln -s %s %s' % ('default', self.site))
        file_path = os.path.join(self.working_dir, file_dir)
        if not os.path.exists(file_path):
            local('mkdir -p %s' % file_path)
            # Create empty .gitignore file so git will track the files directory.
            local('touch %s' % (os.path.join(file_path, '.gitignore')))
        pantheon.create_pantheon_settings_file(destination)

                   
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
            for commit in commits:
                if len(commit) > 1:
                    local("git reset --hard " + commit)
                    difference = int(local("diff -rup " + self.processing_dir + " ./ | wc -l"))
                    print("Commit " + commit + " shows difference of " + str(difference))
                    if match['commit'] == None or difference < match['difference']:
                        match['difference'] = difference
                        match['commit'] = commit
        return match['commit']


    def _get_files_dir(self, env='dev'):
        database = '%s_%s' % (self.project, env)
        # Get file_directory_path directly from database, as we don't have a working drush yet.
        return local("mysql -u %s -p'%s' %s --skip-column-names --batch -e \
                      \"SELECT value FROM variable WHERE name='file_directory_path';\" | \
                        sed 's/^.*\"\(.*\)\".*$/\\1/'" % (self.project,
                                                          self.db_password,
                                                          database)).rstrip('\n')
        



class SiteImport:

    def __init__(self, location, webroot, project, environment):
        if os.path.exists(location):
            self.location = location
            self.project = project
            self.environment = environment
            self.destination = webroot + project + '/' + environment + '/'
            self.drupal = DrupalInstallation(location)
            self.drupal.init_drupal_data()
            self.sql_dumps = self.get_sql_files()
            self.sites = self.get_matched_sites()


    def get_sql_files(self):
        databases = list()
        with cd(self.drupal.location):
            with settings(warn_only=True):
                sql_dumps = (local("find . -maxdepth 1 -type f | grep '\.sql'")).replace('./','').rstrip('\n')
                if not sql_dumps:
                    abort("No .sql files found")
        # One database file
        if '\n' not in sql_dumps:
            databases.append(self.SQLDump(self.drupal.location + sql_dumps))
        # Multiple database file
        else:
            sql_dumps = sql_dumps.split('\n')
            for dump in sql_dumps:
                databases.append(self.SQLDump(self.drupal.location + dump))
        return databases


    def get_matched_sites(self):
        matches = list()
        # If one site and one database, don't test anything just assume they match.
        if self.drupal.valid_site_count() == 1 and self.database_count() == 1:
            for site in self.drupal.sites:
                if site.valid:
                    match = copy.deepcopy(site)
                    match.database.dump = self.sql_dumps[0].sql_file
                    matches.append(match)
        # More than one site and/or database
        else:
            for site in self.drupal.sites:
                if site.valid:
                    for dump in self.sql_dumps:
                        if site.database.name == dump.database_name:
                            match = copy.deepcopy(site)
                            match.database.dump = dump.sql_file
                            matches.append(match)

        # Set site webroot to new destination (webroot + project + environment)
        for match in matches:
            match.webroot = self.destination

        return matches

    def database_count(self):
        return len(self.sql_dumps)


    class SQLDump:

        def __init__(self, sql_file):
            self.sql_file = sql_file
            self.database_name = self.get_database_name(sql_file)


        def get_database_name(self, sql_file):
            # Check for 'USE' statement
            name = (local("grep '^USE `' " + sql_file + r" | sed 's/^.*`\(.*\)`;/\1/'")).rstrip('\n')
            # If multiple databases defined in dump file, abort.
            if '\n' in name:
                abort("Multiple databases found in: " + sql_file)
            # Check dump file comments for database name
            elif not name:
                name = (local(r"awk '/^-- Host:/' " + sql_file \
                    + r" | sed 's_.*Host:\s*\(.*\)\s*Database:\s*\(.*\)$_\2_'")).rstrip('\n')
            # If multiple databases defined in dump file, abort.
            if '\n' in name:
                abort("Multiple databases found in: " + sql_file)
            return name



