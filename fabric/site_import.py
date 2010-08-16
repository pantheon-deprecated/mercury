from fabric.api import *
from os.path import exists
from re import search
from tempfile import mkdtemp
from time import sleep
from pantheon import *
import string
import random

def import_site(site_archive, project = None, environment = None):
    '''Import site archive into a Pantheon server'''
    archive_directory = mkdtemp() + '/'

    if (project == None):
        print("No project selected. Using 'pantheon'")
        project = 'pantheon'
    if (environment == None):
        print("No environment selected. Using 'dev'")
        environment = 'dev'

    unarchive(site_archive, archive_directory)
    server = PantheonServer()
    archive = SiteImport(archive_directory, server.webroot, project, environment)

    _setup_databases(archive)
    _setup_site_files(archive)
    _setup_settings_files(archive)
    _setup_modules(archive)
    _setup_files_directory(archive)
    _setup_permissions(server, archive)
    _run_on_sites(archive.sites, 'cc all')
    _run_on_sites(archive.sites, 'cron')
    server.restart_services()

    local("rm -rf " + archive_directory)

def _setup_databases(archive):
    # Sites are matched to databases. Replace database name with: "project_environment_sitename"
    names = list()
    for site in archive.sites:
        # MySQL allows db names up to 64 chars. Check for & fix name collisions, assuming: 
        # project (up to 16chars) and environment (up to 5chars).
        for length in range(43,0,-1):
            #TODO: Write better fix for collisions
            name = archive.project + '_' + archive.environment + '_' + \
                    site.get_safe_name()[:length] + \
                    str(random.randint(0,9))*(43-length)
            if name not in names:
                break
            if length == 0:
                abort("Database name collision")
        site.database.name = name
        names.append(name)
   
    # Create databases. If multiple sites use same db, only create once.
    databases = set([site.database.name for site in archive.sites])
    for database in databases:
        local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
        local("mysql -u root -e 'CREATE DATABASE %s'" % (database))

    # Create temporary superuser to perform import operations
    with settings(warn_only=True):
        local("mysql -u root -e \"CREATE USER 'pantheon-admin'@'localhost' IDENTIFIED BY '';\"")
    local("mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'pantheon-admin'@'localhost' WITH GRANT OPTION;\"")

    for site in archive.sites:
        # Set grants
        local("mysql -u pantheon-admin -e \"GRANT ALL ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s';\"" % \
                (site.database.name, site.database.username, site.database.password))

        # Strip cache tables, convert MyISAM to InnoDB, and import.
        local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | \
                grep -v '^INSERT INTO `ctools_object_cache`' | \
                grep -v '^INSERT INTO `watchdog`' | \
                grep -v '^INSERT INTO `accesslog`' | \
                grep -v '^USE `' | \
                sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | \
                mysql -u pantheon-admin %s" % \
               (archive.location + site.database.dump, site.database.name))

    # Cleanup
    local("mysql -u pantheon-admin -e \"DROP USER 'pantheon-admin'@'localhost'\"")
    with cd(archive.location):
        local("rm -f *.sql")

def _setup_site_files(archive):
    #TODO: add large file size sanity check (no commits over 20mb)
    #TODO: sanity check for versions prior to 6.6 (no pressflow branch).
    #TODO: look into ignoreing files directory
    #TODO: check for conflicts (hacked core)
    if exists(archive.destination):
        local('rm -r ' + archive.destination)

    # Create vanilla drupal/pressflow branch of same version as import site
    local("git clone " + archive.drupal.branch + " " + archive.destination)

    with cd(archive.destination):
        local("git branch pantheon " + archive.drupal.revision)
        local("git checkout pantheon")

        # Import site and revert any changes to core
        #local("git import-orig " + working_dir)
        local("rm -rf " + archive.destination + "*")
        local("rsync -avz " + archive.location + " " + archive.destination)

        # Cleanup potential issues
        local("rm -f PRESSFLOW.txt")

        # Commit the imported site on top of the closest-match core
        local("git add .")
        print(local("git status"))
        local("git commit -a -m 'Imported site.'")
        print(local("git status"))
        
        # Merge in Latest Pressflow
        local("git checkout master")
        local("git pull git://gitorious.org/pressflow/6.git master")
        local("git checkout pantheon")
        local("git pull . master") # Fails on conflict, commits otherwise.
        
        # TODO: Check for conflicts
        
        # TODO: Is this necessary?
        #local("rm -r ./.git")

def _run_on_sites(sites, cmd):
    for site in sites:
        site.drush(cmd)

def _setup_modules(archive):

    # TODO: add CAS back into the required module list when backend working.
    required_modules = ['apachesolr', 'apachesolr_search', 'cookie_cache_bypass', 'locale', 'syslog', 'varnish']

    if not exists(archive.destination + "sites/all/modules/"):
        local("mkdir " + archive.destination + "sites/all/modules/")

    # Drush will fail if it can't find memcache within drupal install. But we use drush to download memcache. 
    # Solve race condition by downloading outside drupal install. Download other prereqs also.
    temporary_directory = mkdtemp()
    with cd(temporary_directory):
        local("drush dl -y memcache apachesolr cas varnish")
        local("cp -R * " + archive.destination + "sites/all/modules/")
    local("rm -rf " + temporary_directory)
    
    # Run updatedb on all sites
    _run_on_sites(archive.sites, 'updatedb')

    # Make sure all required modules exist in sites/all/modules
    with cd(archive.destination + "sites/all/modules/"):

        # Download SolrPhpClient library
        local("wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz")
        local("mkdir -p ./apachesolr/SolrPhpClient/")
        local("tar xzf SolrPhpClient.r22.2009-11-09.tgz -C ./apachesolr/")
        local("rm SolrPhpClient.r22.2009-11-09.tgz")

        # Download CAS php library
        local("wget http://downloads.jasig.org/cas-clients/php/1.1.2/CAS-1.1.2.tgz")
        local("tar xzf CAS-1.1.2.tgz")
        local("mv ./CAS-1.1.2 ./cas/CAS")
        local("rm CAS-1.1.2.tgz")

    for site in archive.sites:

        # Create new solr index
        solr_path = archive.project + '_' + archive.environment + '_' + site.get_safe_name()
        if exists("/var/solr/" + solr_path):
            local("rm -rf /var/solr/" + solr_path)
        local("cp -R /opt/pantheon/fabric/templates/solr/ /var/solr/" + solr_path)

        with cd(archive.destination + "sites/" + site.name):
           # If required modules exist in specific site directory, make sure they are on latest version.
            if exists("modules"):
                with cd("modules"):
                    if exists("apachesolr"):
                        local("drush dl -y apachesolr")
                    if exists("cas"):
                        local("drush dl -y cas")
                    if exists("memcache"):
                        local("drush dl -y memcache")
                    if exists("varnish"):
                        local("drush dl -y varnish")

        # Enable all required modules
        site.drush('enable', required_modules)

        # Solr variables
        drupal_vars = {}
        drupal_vars['apachesolr_path'] = '/' + solr_path
        drupal_vars['apachesolr_port'] = 8983
        drupal_vars['apachesolr_search_make_default'] = 1
        drupal_vars['apachesolr_search_spellcheck'] = True

        # admin/settings/performance variables
        drupal_vars['cache'] = 'CACHE_EXTERNAL'
        drupal_vars['page_cache_max_age'] = 900
        drupal_vars['block_cache'] = True
        drupal_vars['page_compression'] = 0
        drupal_vars['preprocess_js'] = True
        drupal_vars['preprocess_css'] = True

        # CAS variables
        drupal_vars['cas_server'] = 'login.getpatheon.com'
        drupal_vars['cas_uri'] = '/cas'

        # Set Drupal variables
        with settings(warn_only=True):
            site.set_variables(drupal_vars)

def _setup_files_directory(archive):
    for site in archive.sites:
        site.file_location = site.get_file_location()
        with cd(archive.destination + "sites/" + site.name):
            # if file_directory_path is not set.
            if not site.file_location:
                site.file_location = 'sites/' + site.name + '/files'
                site.set_variables({'file_directory_path':site.file_location})
            # if file_directory_path is set, but doesn't exist, create it.
            if not exists(archive.destination + site.file_location):
                local("mkdir -p " + archive.destination + site.file_location)

def _setup_permissions(server, archive):
    local("chown -R %s:%s %s" % (server.owner, server.group, archive.destination))
    for site in archive.sites:
        # Settings.php Permissions
        with cd(archive.destination + "sites/" + site.name):
            local("chmod 440 settings.php")
        # File directory permissions (770 on all child directories, 660 on all files)
        with cd(archive.destination + site.file_location):
            local("chmod 770 .")
            local("find . -type d -exec find '{}' -type f \; | while read FILE; do chmod 660 \"$FILE\"; done")
            local("find . -type d -exec find '{}' -type d \; | while read DIR; do chmod 770 \"$DIR\"; done")
        # Solr Index permissions
        with cd("/var/solr"):
            local("chown -R %s:%s *" % (server.tomcat_owner, server.tomcat_owner))

def _setup_settings_files(archive):
    slug_template = local("cat /opt/pantheon/fabric/templates/import.settings.php")
    for site in archive.sites:
        # Add project + random string as memcached prefix.
        site.database.memcache_prefix = archive.project + \
                ''.join(["%s" % random.choice(string.ascii_letters + string.digits) for i in range(8)])
        slug = string.Template(slug_template)
        slug = slug.safe_substitute(site.database.__dict__)
        with open(archive.destination + "sites/" + site.name + "/settings.php", 'a') as f:
            f.write(slug)
        f.close


