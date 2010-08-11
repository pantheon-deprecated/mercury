from fabric.api import *
from os.path import exists
from string import Template
from re import search
from tempfile import mkdtemp
from pantheon import *

def import_site(site_archive, base_dir = 'pantheon', environment = 'dev'):
    '''Import site archive into a Pantheon server'''
    archive_directory = mkdtemp() + '/'
    destination = base_dir + '_' + environment

    unarchive(site_archive, archive_directory)

    server = PantheonServer()
    archive = SiteImport(archive_directory, server.webroot, destination)

    _setup_databases(archive, environment)
    _setup_site_files(archive)
    _update_databases(archive)
    _setup_modules(archive)
    _setup_files_directory(archive)
    _setup_settings_files(archive)
    _setup_permissions(server, archive)

    server.restart_services()
    local("rm -rf " + archive_directory)

def _setup_databases(archive, environment):

    # Add environmental suffix (dev/test/live)
    if environment:
        for site in archive.sites:
            # MySQL allows 64 character names. Slice to 59 chars before adding suffix.
            # TODO: make sure this doesn't cause database name collisions.
            site.database.name = site.database.name[:59]
            site.database.name += "_" + environment


    # Create databases. If multiple sites use same db, only create once.
    databases = set([database for database in [site.database.name for site in archive.sites]])
    for database in databases:
        local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
        local("mysql -u root -e 'CREATE DATABASE %s'" % (database))

    # Create temporary superuser to perform import operations
    with settings(warn_only=True):
        local("mysql -u root -e \"DROP USER 'pantheon-admin'@'localhost';\"")
    local("mysql -u root -e \"CREATE USER 'pantheon-admin'@'localhost' IDENTIFIED BY '';\"")
    local("mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'pantheon-admin'@'localhost' WITH GRANT OPTION;\"")

    imported = []
    for site in archive.sites:
        # Set grants
        local("mysql -u pantheon-admin -e \"GRANT ALL ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s';\"" % \
                (site.database.name, site.database.username, site.database.password))

        # If multiple sites use same db, no need to import again.
        if site.database.dump not in imported:
            # Strip cache tables, convert MyISAM to InnoDB, and import.
            local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | \
                    grep -v '^USE `' | \
                    sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | \
                    mysql -u pantheon-admin %s" % \
                   (archive.location + site.database.dump, site.database.name))
            imported.append(site.database.dump)

    # Cleanup
    local("mysql -u pantheon-admin -e \"DROP USER 'pantheon-admin'@'localhost'\"")
    db_dumps = set(site.database.dump for site in archive.sites)
    with cd(archive.location):
        local("rm -f " + " ".join(["%s" % db_dump for db_dump in db_dumps]))

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

def _update_databases(archive):
    for site in archive.sites:
        site.updatedb()

def _setup_modules(archive):

    required_modules = ['apachesolr', 'apachesolr_search', 'cas', 'cookie_cache_bypass', 'locale', 'syslog', 'varnish']

    if not exists(archive.destination + "sites/all/modules/"):
        local("mkdir " + archive.destination + "sites/all/modules/")

    # Drush will fail if it can't find memcache within drupal install. But we use drush to download memcache. 
    # Solve race condition by downloading outside drupal install.
    temporary_directory = mkdtemp()
    with cd(temporary_directory):
        local("drush dl -y memcache")
        local("cp -R memcache " + archive.destination + "sites/all/modules/")
    local("rm -rf " + temporary_directory)

    # Make sure all required modules exist in sites/all/modules
    with cd(archive.destination + "sites/all/modules/"):
        # Warn only. Drush complains if modules already exist.
        with settings(warn_only=True):
            local("drush dl -y apachesolr cas varnish")
            local("drush -y solr-phpclient")

        local("wget http://downloads.jasig.org/cas-clients/php/current/CAS-1.1.2.tgz")
        local("tar xzvf CAS-1.1.2.tgz")
        local("cp -R CAS-1.1.2/CAS ./cas/")
        local("rm -rf CAS-1.1.2")
        local("rm CAS-1.1.2.tgz")

    for site in archive.sites:

        # Create new solr index
        solr_path = archive.env_dir.replace('/','_')
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
            site.enable_modules(required_modules)

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

            # Set Drupal variables
            with settings(warn_only=True):
                site.set_variables(drupal_vars)

def _setup_files_directory(archive):
    for site in archive.sites:
        site.file_location = site.get_file_location()
        with cd(archive.destination + "sites/" + site.name):
            # if file_directory_path is not set, create one and set variable.
            if not site.file_location:
                site.set_file_location("sites/" + site.name + "/files")
            # if file_directory_path is set, but doesn't exist, create it.
            if not exists(archive.destination + site.file_location):
                local("mkdir -p " + archive.destination + self.file_location)

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

def _setup_settings_files(archive):
    slug_template = local("cat /opt/pantheon/fabric/templates/import.settings.php")
    for site in archive.sites:
        # Add env_dir (e.g. pantheon_dev) as memcached prefix.
        site.database.site_location = archive.env_dir.replace('/','_')
        slug = Template(slug_template)
        slug = slug.safe_substitute(site.database.__dict__)
        with open(archive.destination + "sites/" + site.name + "/settings.php", 'a') as f:
            f.write(slug)
        f.close

