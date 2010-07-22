from fabric.api import *
from os.path import exists
from urlparse import urlparse

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

def get_database_settings(settings_file):
    url = (local("awk '/^\$db_url = /' " + settings_file + " | sed 's/^.*'\\''\([a-z]*\):\(.*\)'\\''.*$/\\2/'")).rstrip('\n')

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

    return ret

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

