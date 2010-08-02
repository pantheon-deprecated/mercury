from fabric.api import *
from pantheon import get_server_settings, get_site_settings
from tempfile import mkdtemp
import subprocess
import pipes

def export_site(webroot = None):
    temporary_directory = mkdtemp()

    if (webroot == None):
        print('Using default webroot.')
        webroot = get_server_settings()['webroot']

    print('Exporting to temporary directory %s' % temporary_directory)
    _export_files(webroot, temporary_directory)
    _export_data(webroot, temporary_directory)
    _make_archive(temporary_directory)

def _export_files(webroot, temporary_directory):
    local('git clone %s %s/htdocs' % (webroot, temporary_directory))
    local('rm -rf %s/htdocs/.git' % temporary_directory)

def _export_data(webroot, temporary_directory):
    all_settings = get_site_settings(webroot)
    with cd(temporary_directory + "/htdocs"):
        for site in all_settings:
            site_settings = all_settings[site]
            local('mysqldump --single-transaction --user=%s --password=%s --host=%s %s > %s.sql' % \
              (
                pipes.quote(site_settings['db_username']),
                pipes.quote(site_settings['db_password']),
                pipes.quote(site_settings['db_hostname']),
                pipes.quote(site_settings['db_name']),
                pipes.quote(site_settings['db_name']),
              )    
            )

def _make_archive(directory):
    file = directory + ".tar.gz"
    with cd(directory):
      local('tar czf %s htdocs' % file)
    print('Archived to %s' % file)
    return file
