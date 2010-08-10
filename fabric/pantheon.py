from fabric.api import *
from os.path import exists
from urlparse import urlparse
from re import search
from tempfile import mkdtemp
from copy import deepcopy

def unarchive(archive, destination):
    '''Extract archive to destination directory and remove VCS files'''
    if not exists(archive):
        abort("Archive file \"" + archive + "\" does not exist.")

    if exists(destination):
        local("rm -rf " + destination)

    local("bzr init " + destination)

    with cd(destination):
        local("bzr import " + archive)
        with settings(warn_only=True):
            local("rm -r ./.bzr")
            local("rm -r ./.git")
            local("find . -depth -name .svn -exec rm -fr {} \;")
            local("find . -depth -name CVS -exec rm -fr {} \;")

class DrupalInstallation:

    def __init__(self, location):
        self.location = location
        if exists(location):
            self.version = self.get_drupal_version()
            self.platform =  self.get_drupal_platform()
            self.set_branch_and_revision()
            self.sites = self.get_sites()

    def get_sites(self):
        sites = []
        site_names = self.get_site_names()
        for name in site_names:
            sites.append(self.get_site_data(name))
        return sites

    def get_site_names(self):
        names = list()
        # Get all settings.php files
        with cd(self.location):
            settings_files = (local('find sites/ -name settings.php -type f')).rstrip('\n')
        # Single site
        if '\n' not in settings_files:
            names.append((search(r'^.*sites/(.*)/settings.php', settings_files)).group(1))
        # Multiple sites
        else:
            settings_files = settings_files.split('\n')
            for sfile in settings_files:
                names.append((search(r'^.*sites/(.*)/settings.php',sfile)).group(1))
        return names

    def get_site_data(self, name):
        site = DrupalSite(name, self.location)
        site.database.get_settings(self.location, site.name)
        site.valid = site.database.is_valid()
        return site
    
    def get_drupal_platform(self):
        return ((local("awk \"/\'info\' =>/\" " + self.location + "modules/system/system.module" + \
                r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')).rstrip('\n').upper())

    def get_drupal_version(self):
        return ((local("awk \"/define\(\'VERSION\'/\" " + self.location + "modules/system/system.module" + \
                "| sed \"s_^.*'\(6\)\.\([0-9]\{1,2\}\)'.*_\\1-\\2_\"")).rstrip('\n'))

    def get_pressflow_revision(self):
        #TODO: Optimize this (restrict search to revisions within Drupal minor version)
        #TODO: Add check for Bazaar or git metadata
        temporary_directory = mkdtemp()
        local("git clone git://gitorious.org/pressflow/6.git " + temporary_directory)
        with cd(temporary_directory):
            match = {'difference': None, 'commit': None}
            commits = local("git log | grep '^commit' | sed 's/^commit //'").split('\n')
            for commit in commits:
                if len(commit) > 1:
                    local("git reset --hard " + commit)
                    difference = int(local("diff -rup " + self.location + " ./ | wc -l"))
                    print("Commit " + commit + " shows difference of " + str(difference))
                    if match['commit'] == None or difference < match['difference']:
                        match['difference'] = difference
                        match['commit'] = commit
        return match['commit']

    def set_branch_and_revision(self):
        if self.platform == "DRUPAL":
            self.branch = "git://gitorious.org/drupal/6.git"
            self.revision = "DRUPAL-" + self.version
        elif self.platform == "PRESSFLOW":
            self.branch = "git://gitorious.org/pressflow/6.git"
            self.revision = self.get_pressflow_revision()

    def valid_site_count(self):
        return len([site for site in self.sites if site.valid])


class DrupalSite:

    def __init__(self, name = '', webroot = ''):
        self.name = name
        self.webroot = webroot
        self.database = self.DrupalDB()
        self.file_location = ''
        self.valid = False

    def get_file_location(self):
        return (local("drush --uri=%s variable-get file_directory_path | \
            grep 'file_directory_path: \"' | \
            sed 's/^file_directory_path: \"\(.*\)\".*/\\1/'" % self.name)).rstrip('\n')

    def set_file_location(self, path):
        with settings(warn_only=True):
            with cd(self.webroot):
                local("drush --uri=%s variable-set --always-set file_directory_path %s" % (self.name, path))
        self.file_location = path

    def set_variables(self, variables = dict()):
        with cd(self.webroot):
            for key, value in variables.iteritems():
                # normalize strings and bools
                if isinstance(value, str):
                    value = "'" + value + "'"
                if isinstance(value, bool):
                    if value == True:
                        value = 'TRUE'
                    elif value == False:
                        value= 'FALSE'
                local("drush --uri=%s php-eval \"variable_set('%s',%s);\"" % (self.name, key, value))

    def updatedb(self):
        with cd(self.webroot):
            with settings(warn_only=True):
                local("drush -y --uri=" + self.name + " updatedb")

    def enable_modules(self, modules):
        with settings(warn_only=True):
            local("drush en -y " + " ".join(["%s" % module for module in modules]))


    class DrupalDB:

        def __init__(self):
            self.name = ''
            self.username = ''
            self.password = ''
            self.hostname = ''

        def get_settings(self, webroot, site_name):
            settings_file = webroot + "sites/" + site_name + "/settings.php"
            url = (local("awk '/^\$db_url = /' " + settings_file + \
                  " | sed 's/^.*'\\''\([a-z]*\):\(.*\)'\\''.*$/\\2/'")).rstrip('\n')

            # Use last db connection string
            if '\n' not in url:
                url = urlparse(url)
            else:
                url = url.split('\n')
                url = urlparse(url[len(url)-1])

            if url.password == None: url.password = ''

            self.username = url.username
            self.password = url.password
            self.name = url.path[1:].replace('\n','')
            self.hostname = url.hostname

        def is_valid(self):
            if self.name == None:
                return False
            if self.name == "databasename" \
                    and self.username == "username" \
                    and self.password == "password" \
                    and self.hostname == "hostname": 
                return False
            return True

class PantheonServer:

    def __init__(self):
        # Ubuntu / Debian
        if exists('/etc/debian_version'):
            self.webroot = '/var/www/'
            self.owner = 'root'
            self.group = 'www-data'
            self.distro = 'ubuntu'
        # Centos
        elif exists('/etc/redhat-release'):
            self.webroot = '/var/www/html/'
            self.owner = 'root'
            self.group = 'apache'
            self.distro = 'centos'
        self.ip = (local('hostname --ip-address')).rstrip('\n')

    def restart_services(self):
        if self.distro == 'ubuntu':
            local('/etc/init.d/apache2 restart')
            local('/etc/init.d/memcached restart')
            local('/etc/init.d/tomcat6 restart')
        elif self.distro == 'centos':
            local('/etc/init.d/httpd restart')
            local('/etc/init.d/memcached restart')
            local('/etc/init.d/tomcat5 restart')

class SiteImport:
    
    def __init__(self, location, webroot, env_dir):
        if exists(location):
            self.location = location
            self.env_dir = env_dir
            self.destination = webroot + env_dir + '/'
            self.drupal = DrupalInstallation(location)
            self.sql_dumps = self.get_sql_files()
            self.sites = self.get_matched_sites()
    
    def get_sql_files(self):
        databases = list()
        with cd(self.drupal.location):
            with settings(warn_only=True):
                sql_dumps = (local("find . -maxdepth 1 -type f | grep '\.sql'")).replace('./','').rstrip('\n')
        # One database file
        if '\n' not in sql_dumps:
            databases.append(self.SQLDump(self.drupal.location, sql_dumps))
        # Multiple database file
        else:
            sql_dumps = sql_dumps.split('\n')
            for dump in sql_dumps:
                databases.append(self.SQLDump(self.drupal.location, dump))
        return databases

    def get_matched_sites(self):
        matches = list()
        # If one site and one database, don't test anything just assume they match.
        if self.drupal.valid_site_count() == 1 and self.database_count() == 1:
            for site in self.drupal.sites:
                if site.valid:
                    match = deepcopy(site)
                    match.database.dump = self.sql_dumps[0].file_name
                    matches.append(match)
        # More than one site and/or database
        else:
            for site in self.drupal.sites:
                if site.valid:
                    for dump in self.sql_dumps:
                        if site.database.name == dump.database_name:
                            match = deepcopy(site)
                            match.database.dump = dump.file_name
                            matches.append(match)

        # Set site webroot to new destination
        for match in matches:
            match.webroot = self.destination

        return matches

    def database_count(self):
        return len(self.sql_dumps)

    class SQLDump:

        def __init__(self, location, file_name):
            self.file_name = file_name
            self.database_name = self.get_database_name(location + file_name)

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
            return name

