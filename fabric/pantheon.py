from fabric.api import *
from os.path import exists
from urlparse import urlparse
from re import search

def unarchive(archive, destination):
    '''Extract archive to destination directory and remove VCS files'''
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

def get_site_settings(webroot):
    sites = {}
    # Get all settings.php files
    with cd(webroot):
        settings_files = (local('find sites/ -name settings.php -type f')).rstrip('\n')
    # multiple settings.php files
    if '\n' in settings_files:
        settings_files = settings_files.split('\n')
        # Step through each settings.php file and select sites 
        for sfile in settings_files:
            db_settings = get_database_settings(webroot + sfile)
            if _is_valid_db_url(db_settings):
                site_name = (search(r'^.*sites/(.*)/settings.php',sfile)).group(1)
                sites[site_name] = db_settings
    # Single settings.php
    else:
        db_settings = get_database_settings(webroot + settings_files)
        if _is_valid_db_url(db_settings):
            site_name = (search(r'^.*sites/(.*)/settings.php', settings_files)).group(1)
            sites[site_name] = db_settings
    return sites

def get_database_settings(settings_file):
    url = (local("awk '/^\$db_url = /' " + settings_file + \
              " | sed 's/^.*'\\''\([a-z]*\):\(.*\)'\\''.*$/\\2/'")).rstrip('\n')

    # Check for multiple connection strings. If more than one, use the last.
    if '\n' in url:
        url = url.split('\n')
        url = urlparse(url[len(url)-1])
    else:
        url = urlparse(url)

    ret = {}
    ret['db_username'] = url.username
    ret['db_password'] = url.password
    ret['db_name'] = url.path[1:].replace('\n','')
    ret['db_hostname'] = url.hostname

    return ret

def _is_valid_db_url(database):
    # Invalid: Missing username or databasename 
    if database['db_name'] == None:
        return False
    # Invalid: Set to default values
    elif database['db_username'] == "username" \
        and database['db_password'] == "password" \
        and database['db_name'] == "databasename" \
        and database['db_hostname'] == "localhost":
        return False
    # Valid
    else:
        return True

def get_server_settings():
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
    ret['ip'] = (local('hostname --ip-address')).rstrip('\n')
    return ret

