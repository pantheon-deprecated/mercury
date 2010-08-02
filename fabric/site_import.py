from fabric.api import *
from fabric.operations import prompt
from os.path import exists
from string import Template
from re import search
from pantheon import *

def import_site(site_archive, working_dir='/tmp/import_site/'):
    '''Import site archive into a Pantheon server'''
    unarchive(site_archive, working_dir)

    server_settings = get_server_settings()
    sites = _get_sites(working_dir)
    site_names = sites.keys()
    webroot = server_settings['webroot']
    
    _setup_databases(sites, working_dir)
    _setup_site_files(webroot, working_dir, site_names)
    _setup_modules(webroot, site_names)
    _setup_settings_files(webroot, sites)
    _setup_permissions(server_settings, site_names)

    _restart_services(server_settings['distro'])

#    with cd(server_settings['webroot'] + "sites/"):
#        local("ln -s " + site_settings['site_name'] + " " + server_settings['ip'])

def _get_sites(working_dir):
    match = {}

    exported_sites = get_site_settings(working_dir)
    exported_databases = _get_database_names(working_dir)
    site_count = len(exported_sites)
    db_count = len(exported_databases)
    if len(exported_sites) == 1 and len(exported_databases) == 1:
        # Single Site - Single Database - Assume site matches database
        site = exported_sites.keys()[0]
        match[site] = {}
        match[site]['database'] = exported_sites[site]
        match[site]['database']['db_dump'] = exported_databases.keys()[0]
    else: 
        matched_databases = {}
        for site in exported_sites.keys():
            for db_dump in exported_databases.keys():
                if exported_sites[site]['db_name'] == exported_databases[db_dump]:
                    matched_databases[site] = []
                    if exported_databases[db_dump] not in matched_databases[site]:
                        match[site] = {}
                        match[site]['database'] = exported_sites[site]
                        match[site]['database']['db_dump'] = db_dump
                        # track database names that match a site in case multiple dumps contain databases with same name.
                        matched_databases[site].append(exported_databases[db_dump])
    return match

def _setup_databases(sites, working_dir):
    # Get all databases, and put in a set to remove duplicates. Create a database for each unique database matched to a site. 
    databases = set([database for database in [sites[site]['database']['db_name'] for site in sites]])
    for database in databases:
        local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
        local("mysql -u root -e 'CREATE DATABASE %s'" % (database))
    # Import each database dump that contains a database matched to a site.
    database_settings = [sites[site]['database'] for site in sites]
    _import_databases(database_settings, working_dir)

def _import_databases(databases, working_dir):

    # Create temporary superuser to perform import operations
    with settings(warn_only=True):
        local("mysql -u root -e \"DROP USER 'pantheon-admin'@'localhost';\"")
    local("mysql -u root -e \"CREATE USER 'pantheon-admin'@'localhost' IDENTIFIED BY '';\"")
    local("mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'pantheon-admin'@'localhost' WITH GRANT OPTION;\"")


    imported = []
    # Set grants and import
    for database in databases:
        # Change 'None' to empty string
        if not database['db_password']: database['db_password'] = ''
        local("mysql -u pantheon-admin -e \"GRANT ALL ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s';\"" % \
                (database['db_name'], database['db_username'], database['db_password']))
        if database['db_dump'] not in imported:
            # Strip cache tables, convert MyISAM to InnoDB, and import.
            local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | mysql -u pantheon-admin %s" % \
                    (working_dir + database['db_dump'], database['db_name']))
            # track imported dump files. If multiple sites use same db, no need to import again.
            imported.append(database['db_dump'])

    # Cleanup
    local("mysql -u pantheon-admin -e \"DROP USER 'pantheon-admin'@'localhost'\"")
    db_dumps = set([dump['db_dump'] for dump in databases])
    with cd(working_dir):
        local("rm -f " + " ".join(["%s" % db_dump for db_dump in db_dumps]))

def _get_database_names(webroot):
    databases = {}
    # Get all database dump files
    with cd(webroot):
        with settings(warn_only=True):
            db_dump_files = (local("find . -maxdepth 1 -type f | grep '\.sql'")).replace('./','').rstrip('\n')
    # Multiple database files
    if '\n' in db_dump_files:
        db_dump_files = db_dump_files.split()
        for db_dump in db_dump_files:
            databases[db_dump] = _get_database_name_from_dump(webroot + db_dump)
    # Single database file
    else:
        databases[db_dump_files] = _get_database_name_from_dump(webroot + db_dump_files)
    return databases

def _get_database_name_from_dump(database_dump):
    # Check for 'USE' statement
    databases = (local("grep '^USE `' " + database_dump + r" | sed 's/^.*`\(.*\)`;/\1/'")).rstrip('\n')
    # If multiple databases defined in dump file, abort.
    if '\n' in databases:
        abort("Multiple databases found in: " + database_dump)
    # Check dump file comments for database name
    elif not databases:
        databases = (local(r"awk '/^-- Host:/' " + database_dump \
            + r" | sed 's_.*Host:\s*\(.*\)\s*Database:\s*\(.*\)$_\2_'")).rstrip('\n')
    return databases

def _get_drupal_version(working_dir):
    # Test 1: Try to get version from system.module
    version = (local("awk \"/define\(\'VERSION\'/\" " + working_dir + "modules/system/system.module" + "| sed \"s_^.*'\(6\)\.\([0-9]\{1,2\}\)'.*_\\1-\\2_\"")).rstrip('\n')
    if not version:
        # Test 2: Try to get drupal version from system.info
        version = (local("awk '/version/ {if ($3 != \"VERSION\") print $3}' " + working_dir + "modules/system/system.info" + r' | sed "s_^\"\(6\)\.\([0-9]\{1,2\}\)\".*_\1-\2_"')).rstrip('\n')
    if not version:
        # Test 3: Try to get drupal version from Changelog
        version = (local("cat " + working_dir  + "CHANGELOG.txt | grep --max-count=1 Drupal | sed 's/Drupal \([0-9]\)*\.\([0-9]*\).*/\\1-\\2/'")).rstrip('\n')
    if not version:
        abort("Unable to determine Drupal version.")
    else:
        return version

def _get_pressflow_revision(working_dir, drupal_version):
    #TODO: Optimize this (restrict search to revisions within Drupal minor version)
    #TODO: Add check for Bazaar or git metadata
    
    # PRESSFLOW.txt is currently not usable to identify a git commit.
    #if exists(working_dir + 'PRESSFLOW.txt'):
    #    revno = local("cat " + working_dir + "PRESSFLOW.txt").split('.')[2].rstrip('\n')
    #    return revno
    if exists("/tmp/pf_temp"):
        local("rm -rf /tmp/pf_temp")
    local("git clone git://gitorious.org/pressflow/6.git /tmp/pf_temp")
    with cd("/tmp/pf_temp"):
        match = {'difference': None, 'commit': None}
        commits = local("git log --max-count=1 | grep '^commit' | sed 's/^commit //'").split('\n')
        for commit in commits:
            local("git reset --hard " + commit)
            difference = int(local("diff -rup " + working_dir + " ./ | wc -l"))
            if match['commit'] == None or difference < match['difference']:
                match['difference'] = difference
                match['commit'] = commit
    return match['commit']
        
def _get_branch_and_revision(working_dir):
    #TODO: pressflow.txt  doesn't exists if pulled from version control
    #TODO: check that it is Drupal V6

    ret = {}
    drupal_version = (_get_drupal_version(working_dir)).rstrip('\n')
    # Check if site uses Pressflow (look in system.module)
    dist = (local("awk \"/\'info\' =>/\" " + working_dir + "modules/system/system.module" + r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')).rstrip('\n')
    if dist == 'Drupal':
        ret['branch'] = "git://gitorious.org/drupal/6.git"
        ret['revision'] = "DRUPAL-" + drupal_version 
        ret['type'] = "DRUPAL"
    elif dist == 'Pressflow':
        revision = _get_pressflow_revision(working_dir, drupal_version)
        ret['branch'] = "git://gitorious.org/pressflow/6.git"
        ret['revision'] = revision 
        ret['type'] = "PRESSFLOW"
    else:
        abort("Cannot determine if using Drupal or Pressflow")

    if (ret['revision'] == None) or (ret['revision'] == "tag:DRUPAL-"):
        abort("Unable to determine base Drupal / Pressflow version")

    return ret

def _setup_site_files(webroot, working_dir, sites):
    #TODO: add large file size sanity check (no commits over 20mb)
    #TODO: sanity check for versions prior to 6.6 (no pressflow branch).
    #TODO: look into ignoreing files directory
    #TODO: check for conflicts (hacked core)
    
    if exists(webroot):
        local('rm -r ' + webroot)

    # Create vanilla drupal/pressflow branch of same version as import site
    version = _get_branch_and_revision(working_dir)
    local("git clone " + version['branch'] + " " + webroot)

    with cd(webroot):
        local("git branch pantheon " + version['revision'])
        local("git checkout pantheon")

        # Import site and revert any changes to core
        #local("git import-orig " + working_dir)
        local("rsync -avz " + working_dir + " " + webroot)

        # TODO: What is this for?
        #reverted = local("git reset --hard")

        # Cleanup potential issues
        local("rm -f PRESSFLOW.txt")

				# Commit the imported site on top of the closest-match core
        local("git add .")
        local("git commit -a -m 'Imported site.'")
        
        # Merge in Latest Pressflow
        local("git checkout master")
        local("git pull git://gitorious.org/pressflow/6.git master")
        local("git checkout pantheon")
        local("git pull . master") # Should automatically commit.
        
        # TODO: Check for conflicts
        
        # TODO: Is this necessary?
        #local("rm -r ./.git")
        
        # Run update.php. Wrap in warn_only because drush returns failure if it doesn't need to run.
        with settings(warn_only=True):
            for site in sites:
                local("drush -y --uri=" + site + " updatedb")

def _setup_modules(webroot, sites):

    required_modules = ['apachesolr', 'apachesolr_search', 'cookie_cache_bypass', 'locale', 'syslog', 'varnish']

    # Make sure all required modules exist in sites/all/modules
    if not exists(webroot + "sites/all/modules/"):
        local("mkdir " + webroot + "sites/all/modules/")
    with cd(webroot + "sites/all/modules/"):
        with settings(warn_only=True):
            local("drush dl -y apachesolr memcache varnish")
        local("wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz")
        local("mkdir -p " + webroot + "sites/all/modules/apachesolr/SolrPhpClient/")
        local("tar xzf SolrPhpClient.r22.2009-11-09.tgz -C " + webroot  + "sites/all/modules/apachesolr/")
        local("rm SolrPhpClient.r22.2009-11-09.tgz")
    for site in sites:
        with cd(webroot + "sites/" + site):
            # If required modules exist in specific site directory, make sure they are on latest version.
            if exists("modules"):
                with cd("modules"):
                    if exists("apachesolr"):
                        local("drush dl -y apachesolr")
                    if exists("memcache"):
                        local("drush dl -y memcache")
                    if exists("varnish"):
                        local("drush dl -y varnish")
            # Enable all required modules
            with settings(warn_only=True):
                local("drush en -y " + " ".join(["%s" % module for module in required_modules]))

            # Set apachesolr variables (use php-eval because drush vset always sets as string)
            local("drush php-eval \"variable_set('apachesolr_path', '/default');\"")
            local("drush php-eval \"variable_set('apachesolr_port', 8983);\"")
            local("drush php-eval \"variable_set('apachesolr_search_make_default', 1);\"")
            local("drush php-eval \"variable_set('apachesolr_search_spellcheck', TRUE);\"")

            # Set admin/settings/performance variables
            local("drush php-eval \"variable_set('cache', CACHE_EXTERNAL);\"")
            local("drush php-eval \"variable_set('page_cache_max_age', 900);\"")
            local("drush php-eval \"variable_set('block_cache', TRUE);\"")
            local("drush php-eval \"variable_set('page_compression', 0);\"")
            local("drush php-eval \"variable_set('preprocess_js', TRUE);\"")
            local("drush php-eval \"variable_set('preprocess_css', TRUE);\"")

def _setup_permissions(server_settings, sites):
    file_paths = []
    local("chown -R %(owner)s:%(group)s %(webroot)s" % server_settings)
    for site in sites:
        with cd(server_settings['webroot'] + "sites/" + site):
            local("chmod 440 settings.php")
            file_path = (local("drush variable-get file_directory_path | grep 'file_directory_path: \"' | sed 's/^file_directory_path: \"\(.*\)\".*/\\1/'")).rstrip('\n')
            # if file_directory_path is not set, create one and set variable.
            if not file_path:
                local("mkdir -p files")
                file_path = "sites/" + site + "/files"
                with settings(warn_only=True):
                    local("drush variable-set --always-set file_directory_path " + file_path)
            # if file_directory_path is set, but doesn't exist, create it.
            if not exists(server_settings['webroot'] + file_path):
                local("mkdir -p " + server_settings['webroot'] + file_path)
            file_paths.append(file_path)
    for file_path in set(file_paths):
        with cd(server_settings['webroot'] + file_path):
            local("chmod 770 .")
            local("find . -type d -exec find '{}' -type f \; | while read FILE; do chmod 550 \"$FILE\"; done")
            local("find . -type d -exec find '{}' -type d \; | while read DIR; do chmod 770 \"$DIR\"; done")

def _restart_services(distro):
    if distro == 'ubuntu':
        local('/etc/init.d/apache2 restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat6 restart')
    elif distro == 'centos':
        local('/etc/init.d/httpd restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat5 restart')

def _setup_settings_files(webroot, sites):
    slug_template = local("cat /opt/pantheon/fabric/templates/pantheon.settings.php")
    for site_name, site_values in sites.iteritems():
        if site_values['database']['db_password']:
            site_values['database']['db_password'] = ":" + site_values['database']['db_password']
        slug = Template(slug_template)
        slug = slug.safe_substitute(site_values['database'])
        with open(webroot + "sites/" + site_name + "/settings.php", 'a') as f:
            f.write(slug)
        f.close

