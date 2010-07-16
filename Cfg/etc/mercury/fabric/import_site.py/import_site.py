from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from fabric.operations import prompt
from urlparse import urlparse
from os.path import exists
from string import Template
from pprint import pprint
import pdb

def unarchive(archive, destination):

    if not exists(archive):
        abort("Archive file \"" + archive + "\" does not exist.")

    if exists(destination):
        local("rm -rf " + destination)

    local("bzr init " + destination)

    with cd(destination):
        local("bzr import " + archive)
        local("rm -r ./.bzr")
        local("find . -depth -name .svn -exec rm -fr {} \;")
        local("find . -depth -name CVS -exec rm -fr {} \;")

def is_valid_db(db_info):

    # Check for problems
    if db_info['username'] == None or db_info['password'] == None or db_info['database'] == None:
        # Invalid db connection string (missing information)
        return False
    elif db_info['username'] == "username" and db_info['password'] == "password" and db_info['database'] == "databasename":
        # Connection string is still set to default values
        return False
    elif  ('/' or '\\' or '.') in db_info['database']:
        # Invalid characters in database name
        return False
    else:
        return True

def get_site_settings(working_dir, settings_file):

    url = (local("awk '/^\$db_url = /' " + working_dir + settings_file + " | sed 's/^.*'\\''\([a-z]*\):\(.*\)'\\''.*$/\\2/'")).rstrip('\n')

    # Check for multiple connection strings. If more than one, use the last.
    if '\n' in url:
        url = url.split('\n')
        url = urlparse(url[len(url)-1])
    else:
        url = urlparse(url)

    ret = {}
    ret['username'] = url.username
    ret['password'] = url.password
    ret['database'] = url.path[1:].replace('\n','')
    ret['site_dir'] = settings_file.replace('sites/','').replace('settings.php','')
    
    return ret

def get_settings(working_dir):
    site_settings = {}
    match = []
    # Get all settings.php files
    with cd(working_dir):
        settings_files = (local('find sites/ -name settings.php -type f')).rstrip('\n')

    # Check if any settings.php files were found
    if not settings_files:
        return False

    # multiple settings.php files
    if '\n' in settings_files:
        settings_files = settings_files.split('\n')
        # Step through each settings.php file and select a valid settings.php (with preference for sites/default/)
        for sfile in settings_files:
            site_settings = get_site_settings(working_dir, sfile)
            if is_valid_db(site_settings):
                match.append(site_settings)
        if match.count > 1:
            return choose_site(match, working_dir)
        elif match.count == 1:
            return match.pop()

    # Single settings.php
    else:
        site_settings = get_site_settings(working_dir, settings_files)
        if is_valid_db(site_settings):
            return site_settings
    
    abort("No valid settings.php was found")

def choose_site(sites, working_dir):
    # Try to autmatically figure out which site to use first.

    # Test 1: if db name in the dump file comments match the db name in only one settings.php, this is a safe match.
    found = []
    # If we need it, host is in back-reference 1 (\1)
    dumped_db_name = (local(r"awk '/^-- Host:/' " + get_db_dump_name(working_dir) + r" | sed 's_.*Host:\s*\(.*\)\s*Database:\s*\(.*\)$_\2_'")).rstrip('\n')
    for site in sites:
        if site['database'] == dumped_db_name:
            found.append(site)
    if found.count == 1:
        return found.pop()
    elif found.count == 0:
        print "WARNING: The database that was dumped does not match any Drupal settings.php files."

    # Resort to manual
    print "\nMultiple sites found. Please select the site you wish to use:\n"
    count = 0
    for site in sites:
        print "[" + str(count) + "]: " + sites[count]['site_dir']
        count += 1
    valid = False
    while not valid:
        choice = int(prompt('\nChoose Site: \n', validate=r'^\d{1,3}$'))
        if choice < len(sites) and choice > -1:
            valid = True
    return sites[choice]

def get_env_vars():
    '''Get distribution name and return environmental variables based on distribution defaults.'''
    #TODO: Do we need more specific ubuntu versions (e.g. check for lucid for upstart services?)
    ret = {}
    # Default Ubuntu
    if exists('/etc/debian_version'):
        ret['webroot'] = '/var/www/'
        ret['owner'] = 'root'
        ret['group'] = 'www-data'
        ret['distro'] = 'ubuntu'
    # Default Centos
    elif exists('/etc/redhat-release'):
        ret['webroot'] = '/var/www/html/'
        ret['owner'] = 'root'
        ret['group'] = 'apache'
        ret['distro'] = 'centos'
    return ret

def get_drupal_version(working_dir):
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

def get_pressflow_revision(working_dir, drupal_version):
    #TODO: Optimize this (restrict search to revisions within Drupal minor version)
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
        
def get_branch_and_revision(working_dir):
    #TODO: pressflow.txt  doesn't exists if pulled from bzr
    #TODO: check that it is Drupal V6

    ret = {}
    drupal_version = (get_drupal_version(working_dir)).rstrip('\n')
    # Check if site uses Pressflow (look in system.module)
    dist = (local("awk \"/\'info\' =>/\" " + working_dir + "modules/system/system.module" + r' | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')).rstrip('\n')
    if dist == 'Drupal':
        ret['branch'] = "lp:drupal/6.x-stable"
        ret['revision'] = "tag:DRUPAL-" + drupal_version 
        ret['type'] = "DRUPAL"
    elif dist == 'Pressflow':
        revision = get_pressflow_revision(working_dir, drupal_version)
        ret['branch'] = "lp:pressflow/6.x"
        ret['revision'] = revision 
        ret['type'] = "PRESSFLOW"
    else:
        abort("Cannot determine if using Drupal or Pressflow")

    if (ret['revision'] == None) or (ret['revision'] == "tag:DRUPAL-"):
        abort("Unable to determine base Drupal / Pressflow version")

    return ret

def get_db_dump_name(working_dir):
    with settings(warn_only=True):
        db_dump_file = local("ls " + working_dir + "*.sql")
    
    # Test for no .sql files
    if db_dump_file.failed:
        abort("ERROR: No database dump file (*.sql) found.")

    # Test for multiple .sql files
    db_dump_file = db_dump_file.rstrip('\n')
    if '\n' in db_dump_file:
        abort("ERROR: Multiple database dump files (.sql) found.")

    return db_dump_file

def import_database(db_info, working_dir):

    db_dump_file = get_db_dump_name(working_dir)

    local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS " + db_info['database'] + "'")
    local("mysql -u root -e \"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, LOCK TABLES, CREATE TEMPORARY TABLES ON " + db_info['database'] + ".* TO '" + db_info['username'] + "'@'localhost' IDENTIFIED BY '" + db_info['password'] + "';\"")
    local("mysql -u root -e 'FLUSH PRIVILEGES;'")
    local("mysql -u root " + db_info['database'] + " < " + db_dump_file)
    local("rm -f " + db_dump_file)

def setup_site_files(webroot, site, working_dir):
    #TODO: add large file size sanity check (no commits over 20mb)
    #TODO: sanity check for versions prior to 6.6 (no pressflow branch).
    #TODO: test wildcard in ignore
    #TODO: look into ignoreing files directory
    #TODO: sanity check for conflicts (hacked core)
    #TODO: check if updatedb needs to run. Fabric will return error if it doesn't need to run.
    
    if exists(webroot):
        local('rm -r ' + webroot)

    # Create vanilla drupal/pressflow branch of same version as import site
    version = get_branch_and_revision(working_dir)

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

def update_settings(webroot, db_info):
    #TODO: remove any previously defined $db_url strings rather than relying on ours being last
    slug = Template(local("cat /etc/mercury/templates/mercury.settings.php"))
    slug = slug.safe_substitute(db_info)
    with open(webroot + "sites/default/settings.php", 'a') as f:
        f.write(slug)
    f.close

def get_module_status(site_path):
    #TODO: extend drush so that "drush pm-list" can have xml/json friendly output. Below is temporary stop-gap
    with cd(site_path):
        # Output module status in dictionary friendly format.
        site_modules = local("drush sql-query \"SELECT name, status FROM system WHERE type='module';\" | awk -v sq=\"'\" '{if ($1 != \"name\" && $2 == 1) print \"(\"sq$1sq\", \"sq\"Enabled\"sq\")\"; if ($1 != \"name\" && $2 == 0) print \"(\"sq$1sq\", \"sq\"Disabled\"sq\")\" }'").replace('\n',',')[:-1]
    return dict(eval(site_modules))

def setup_modules(webroot, site):

    required_modules = {'apachesolr':None, 'apachesolr_search':'disabled', 'cookie_cache_bypass':'Disabled', 'locale':None, 'memcache_admin':None, 'syslog':None, 'varnish':None}

    # Get module dictionary. Key=Module name, Value=Enabled/Disabled/None
    site_modules = get_module_status(webroot + "sites/" + site)

    with cd(webroot):
        # If a required module is found, the value is set to site_modules current status (Enabled/Disabled). If not found, value=None.
        for name in required_modules.keys():
            if site_modules.has_key(name):
                required_modules[name] = site_modules[name]

        # Special case: download memcache if memcache_admin doesn't exist, but don't enable memcache_admin.
        if required_modules['memcache_admin'] == None:
            local("drush -y dl memcache")
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
    site_modules = get_module_status(webroot)
    check_modules = ['apachesolr', 'apachesolr_search', 'cookie_cache_bypass', 'locale', 'syslog', 'varnish']
    for module in check_modules:
        if site_modules[module] == 'Disabled':
            print "WARNING: Required module \"" + module + "\" could not be enabled."

def set_permissions(site_info):

    # setup ownership and permissions
    local('chown -R ' + site_info['owner'] + ':' + site_info['group'] + ' ' + site_info['webroot'])
    local('chmod 440 ' + site_info['webroot'] + 'sites/default/settings.php')

    #TODO: where do we want to set the start point for searching for 'files' directories (to change perms)?
    # make sure everything under the 'files' directory has proper perms (770 on dirs, 550 on files)
    with cd(site_info['webroot'] + '/sites/'):
        local("find . -type d -name files -exec chmod ug=rwx,o= '{}' \;")
        local("find . -name files -type d -exec find '{}' -type f \; | while read FILE; do chmod ug=rw,o= \"$FILE\"; done")
        local("find . -name files -type d -exec find '{}' -type d \; | while read DIR; do chmod ug=rwx,o= \"$DIR\"; done")

def restart_services(distro):
    if distro == 'ubuntu':
        local('/etc/init.d/apache2 restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat6 restart')
    elif distro == 'centos':
        local('/etc/init.d/httpd restart')
        local('/etc/init.d/memcached restart')
        local('/etc/init.d/tomcat5 restart')

def import_site(site_archive, working_dir='/tmp/import_site/'):
    
    unarchive(site_archive, working_dir)

    settings_info = get_settings(working_dir)
    site_info = get_env_vars()
    #TODO: clean this up.
    site_info['site_dir'] = settings_info['site_dir']

    import_database(settings_info, working_dir)
    setup_site_files(site_info['webroot'], site_info['site_dir'], working_dir)
    setup_modules(site_info['webroot'], site_info['site_dir'])
    update_settings(site_info['webroot'], settings_info)
    set_permissions(site_info)
    restart_services(site_info['distro'])

    #TODO: Write cleanup function
    #TODO: clear solr index (if exists) before using new site

