from fabric.api import *
from fabric.operations import prompt
from os.path import exists
from string import Template
from re import search
from pantheon import *

def import_site(site_archive, working_dir='/tmp/import_site/'):
    '''Import site archive into a Pantheon server'''
    server_settings = get_server_settings()
    unarchive(site_archive, working_dir)
    sites = get_sites(working_dir)
    sanity_check(sites)
    setup_databases(sites)

#    _import_database(site_settings, working_dir)
#    _setup_site_files(server_settings['webroot'], site_settings['site_name'], working_dir)
#    _setup_modules(server_settings['webroot'], site_settings['site_name'])
#    _update_settings(server_settings['webroot'], site_settings)
#    _set_permissions(server_settings, site_settings['site_name'])

#    with cd(server_settings['webroot'] + "sites/"):
#        local("ln -s " + site_settings['site_name'] + " " + server_settings['ip'])

#    _restart_services(server_settings['distro'])

def get_sites(working_dir):
    matched_sites = [] 

    sites = get_site_settings(working_dir)
    databases = _get_database_names(working_dir)
    
    site_count = len(sites)
    db_count = len(databases)
    # Single Database
    if db_count == 1:
        # Single Site - Single Database - Assume site matches database
        if site_count == 1:
            sites[sites.keys()[0]]['db_dump'] = databases.keys()[0]
        # Multiple Sites - Single Databse - Check for matches based on database name
        elif site_count > 1:
            for site in sites:
                if sites[site]['db_name'] == databases.values()[0]:
                    sites[site]['db_dump'] = databases.keys()[0]
            matched_sites.append(sites)
        else:
            pass # no matches found

    # Multiple Databases
    elif  database.count() > 1:
        pass
    else:
        pass #no matches found
    return matched_sites

def setup_databases(sites, working_dir):
    # Create a database for each dumpfile that contains a database matched to a site.
    for database in [sites[site]['db_dump'] for site in sites]:
        create_database(database)
    import_database(sites)

def create_database(database):
    local("mysql -u root -e 'DROP DATABASE IF EXISTS '%s'" % (database))
    local("mysql -u root -e 'CREATE DATABASE '%s'" % (database))

def import_databases(sites):
    dump_files = []
    databases = []
    for db_dump in [sites[site]['db_dump'] for site in sites]:
        pass
    
 
#def build_sites(sites):

    #import database
    #setup site files
    #setup modules
    #update_settings
    #set permissions

def sanity_check(sites):
    # Check that valid sites exist
    if not sites:
        abort("No Valid Drupal Sites Found")

    # Check for multiple databses with the same name
    found = []
    for site in sites:
        for database in site['database']:
            if database in found:
                abort("Multiple databases with the same name.")
            else:
                found.append(database)

def _get_database_names(webroot):
    ''' Returns a dictionary of databases in the form of: databases[dump_filename][databasenames].''' 
    databases = {}
    # Get all database dump files
    with cd(webroot):
        db_dump_files = (local("find . -maxdepth 1 -type f -name *.sql")).lstrip('./').rstrip('\n')
    # Multiple database files
    if '\n' in db_dump_files:
        db_dump_files = db_dump_files.split()
        for db in db_dump_files:
            databases[db] = _get_database_name_from_dump(webroot + db)
    # Single database file
    else:
        databases[db_dump_files] = _get_database_name_from_dump(webroot + db_dump_files)
    return databases

def _get_database_name_from_dump(database_dump):
    # Check for 'USE' directive (multiple databases possible)
    databases = (local("grep '^USE `' " + database_dump + r" | sed 's/^.*`\(.*\)`;/\1/'")).rstrip('\n')
    if databases:
        return databases.split('\n')
    # Check dump file comments for database name
    else:
        databases = (local(r"awk '/^-- Host:/' " + database_dump \
            + r" | sed 's_.*Host:\s*\(.*\)\s*Database:\s*\(.*\)$_\2_'")).rstrip('\n')
        return databases.split('\n')

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
    #TODO: Add check for .bzr metadata
    if exists(working_dir + 'PRESSFLOW.txt'):
        revno = local("cat " + working_dir + "PRESSFLOW.txt").split('.')[2].rstrip('\n')
        return revno
    if exists("/tmp/pf_temp"):
        local("rm -rf /tmp/pf_temp")
    local("bzr branch lp:pressflow/6.x /tmp/pf_temp")
    with cd("/tmp/pf_temp"):
        match = {'num':100000,'revno':0}
        revno = local("bzr revno").rstrip('\n')
        for i in range(int(revno),0,-1):
            local("bzr revert -r" + str(i))
            diff = int(local("diff -rup " + working_dir + " ./ | wc -l"))
            if diff < match['num']:
                match['num'] = diff
                match['revno'] = i
    return str(match['revno'])
        
def _get_branch_and_revision(working_dir):
    #TODO: pressflow.txt  doesn't exists if pulled from bzr
    #TODO: check that it is Drupal V6

    ret = {}
    drupal_version = (_get_drupal_version(working_dir)).rstrip('\n')
    # Check if site uses Pressflow (look in system.module)
    dist = (local("awk \"/\'info\' =>/\" " + working_dir + "modules/system/system.module" + r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')).rstrip('\n')
    if dist == 'Drupal':
        ret['branch'] = "lp:drupal/6.x-stable"
        ret['revision'] = "tag:DRUPAL-" + drupal_version 
        ret['type'] = "DRUPAL"
    elif dist == 'Pressflow':
        revision = _get_pressflow_revision(working_dir, drupal_version)
        ret['branch'] = "lp:pressflow/6.x"
        ret['revision'] = revision 
        ret['type'] = "PRESSFLOW"
    else:
        abort("Cannot determine if using Drupal or Pressflow")

    if (ret['revision'] == None) or (ret['revision'] == "tag:DRUPAL-"):
        abort("Unable to determine base Drupal / Pressflow version")

    return ret

def _import_database(db, working_dir):

    db_dump_file = _get_db_dump_name(working_dir)
    #TODO: break drop and create database into own function
    local("mysql -u root -e 'DROP DATABASE IF EXISTS " + db['db_name'] + "'")
    local("mysql -u root -e 'CREATE DATABASE " + db['db_name'] + "'")
    local("mysql -u root -e \"GRANT ALL ON " + db['db_name'] + ".* TO '" + db['db_username'] + "'@'localhost' IDENTIFIED BY '" + db['db_password'] + "';\"")
    local("cat " + db_dump_file + " | grep -v '^INSERT INTO `cache[_a-z]*`' | sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | mysql -u root " + db['db_name'])
    local("rm -f " + db_dump_file)

def _setup_site_files(webroot, site, working_dir):
    #TODO: add large file size sanity check (no commits over 20mb)
    #TODO: sanity check for versions prior to 6.6 (no pressflow branch).
    #TODO: test wildcard in ignore
    #TODO: look into ignoreing files directory
    #TODO: sanity check for conflicts (hacked core)
    #TODO: check if updatedb needs to run. Fabric will return error if it doesn't need to run.
    
    if exists(webroot):
        local('rm -r ' + webroot)

    # Create vanilla drupal/pressflow branch of same version as import site
    version = _get_branch_and_revision(working_dir)

    local("bzr branch -r " + version['revision'] + " " + version['branch'] + " " + webroot)

    # Bring import site up to current Pressflow version
    with cd(webroot):

        # Import site and revert any changes to core
        local("bzr import " + working_dir)
        reverted = local("bzr revert")

        # Cleanup potential issues
        local("rm -f PRESSFLOW.txt")
        #if exists(".bzrignore"):
        #    local('bzr revert .bzrignore')

        # Magic Happens
        #local("bzr add")
        local("bzr commit --unchanged -m 'Automated Commit'")
        local("bzr merge lp:pressflow/6.x")
        local("rm -r ./.bzr")
#local("bzr commit --unchanged -m 'Update to latest Pressflow core'")
        
        # Run update.php. Wrap in warn_only because drush returns failure if it doesn't need to run.
        with settings(warn_only=True):
            local("drush -y --uri=" + site + " updatedb")

    # Save reverted files as hudson build artifacts
    #with open('/var/lib/hudson/jobs/import_site/workspace/reverted.txt', 'w') as f:
    #    f.write(reverted)
    #f.close

def _update_settings(webroot, site_settings):
    #TODO: remove any previously defined $db_url strings rather than relying on ours being last
    slug = Template(local("cat /opt/pantheon/fabric/templates/pantheon.settings.php"))
    slug = slug.safe_substitute(site_settings)
    with open(webroot + "sites/" + site_settings['site_name'] + "/settings.php", 'a') as f:
        f.write(slug)
    f.close

def _get_module_status(site_path):
    #TODO: extend drush so that "drush pm-list" can have xml/json friendly output. Below is temporary stop-gap
    with cd(site_path):
        # Output module status in dictionary friendly format.
        site_modules = local("drush sql-query \"SELECT name, status FROM system WHERE type='module';\" | awk -v sq=\"'\" '{if ($1 != \"name\" && $2 == 1) print \"(\"sq$1sq\", \"sq\"Enabled\"sq\")\"; if ($1 != \"name\" && $2 == 0) print \"(\"sq$1sq\", \"sq\"Disabled\"sq\")\" }'").replace('\n',',')[:-1]
    return dict(eval(site_modules))

def _setup_modules(webroot, site):

    required_modules = {'apachesolr':None, 'apachesolr_search':'Disabled', 'cookie_cache_bypass':'Disabled', 'locale':None, 'memcache_admin':None, 'syslog':None, 'varnish':None}

    # Get module dictionary. Key=Module name, Value=Enabled/Disabled/None
    site_modules = _get_module_status(webroot + "sites/" + site)

    with cd(webroot):
        # If a required module is found, the value is set to site_modules current status (Enabled/Disabled). If not found, value=None.
        for name in required_modules.keys():
            if site_modules.has_key(name):
                required_modules[name] = site_modules[name]

        # Special case: download memcache if memcache_admin doesn't exist, but don't enable memcache_admin.
        if required_modules['memcache_admin'] == None:
            local("drush -y dl memcache")
            required_modules['memcache_admin'] = 'Disabled'
        if required_modules['memcache_admin'] == 'Disabled':
            del(required_modules['memcache_admin'])

        # Special Case: Make sure both apachesolr and apachesolr_search are installed and enabled.
        if required_modules['apachesolr'] == None:
            local("drush -y dl apachesolr")
            required_modules['apachesolr'] = 'Disabled'
            required_modules['apachesolr_search'] = 'Disabled'
        if required_modules['apachesolr'] == 'Disabled':
            local("wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz")
            local("mkdir -p " + webroot + "sites/all/modules/apachesolr/SolrPhpClient/")
            local("tar xzf SolrPhpClient.r22.2009-11-09.tgz -C " + webroot  + "sites/all/modules/apachesolr/")
            with settings(warn_only=True):
                local("drush -y --uri=" + site + " en apachesolr")
            del(required_modules['apachesolr'])
        if required_modules['apachesolr_search'] == 'Disabled':
            with settings(warn_only=True):
                local("drush -y --uri=" + site + " en apachesolr_search")
            del(required_modules['apachesolr_search'])

        # Normal Cases: Download if absent & enable if disabled.
        for module, status in required_modules.iteritems():
            if status == None:
                local("drush -y dl " + module)
                status = 'Disabled' 
            if status == 'Disabled':
                with settings(warn_only=True):
                    local("drush -y --uri=" + site + " en " + module)

    with cd(webroot + "sites/" + site):
        # Set apachesolr variables
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

    # Drush will report failure if we try to enable a module that is already enabled.
    # To get around this, we wrap "drush en" in warn_only=True.
    # However, we still want to make sure the modules are enabled (and didn't fail for another reason).
    site_modules = _get_module_status(webroot + "sites/" + site)
    check_modules = ['apachesolr', 'apachesolr_search', 'cookie_cache_bypass', 'locale', 'syslog', 'varnish']
    for module in check_modules:
        if site_modules[module] == 'Disabled':
            print "WARNING: Required module \"" + module + "\" could not be enabled."

def _set_permissions(server_settings, site_name):
    #TODO: make database call to find file dir location for specific site
    # setup ownership and permissions
    local('chown -R ' + server_settings['owner'] + ':' + server_settings['group'] + ' ' + server_settings['webroot'])
    local('chmod 440 ' + server_settings['webroot'] + 'sites/' + site_name + '/settings.php')

    # make sure everything under the 'files' directory has proper perms (770 on dirs, 550 on files)
    with cd(server_settings['webroot'] + 'sites/'):
        local("find . -type d -name files -exec chmod ug=rwx,o= '{}' \;")
        local("find . -name files -type d -exec find '{}' -type f \; | while read FILE; do chmod ug=rw,o= \"$FILE\"; done")
        local("find . -name files -type d -exec find '{}' -type d \; | while read DIR; do chmod ug=rwx,o= \"$DIR\"; done")

def _restart_services(distro):
    if distro == 'ubuntu':
        local('/etc/init.d/apache2 restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat6 restart')
    elif distro == 'centos':
        local('/etc/init.d/httpd restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat5 restart')

