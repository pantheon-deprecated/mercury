from fabric.api import *
from pantheon import PantheonServer, DrupalInstallation
from tempfile import mkdtemp
import subprocess
import pipes

def export_site(webroot = None):
    temporary_directory = mkdtemp()

    if (webroot == None):
        print('Using default webroot.')
        server = PantheonServer()
        webroot = server.webroot

    print('Exporting to temporary directory %s' % temporary_directory)
    _export_files(webroot, temporary_directory)
    _export_data(webroot, temporary_directory)
    _make_archive(temporary_directory)

def _export_files(webroot, temporary_directory):
    local('git clone %s %s/htdocs' % (webroot, temporary_directory))
    local('rm -rf %s/htdocs/.git' % temporary_directory)

def _export_data(webroot, temporary_directory):
    drupal = DrupalInstallation(webroot)
    with cd(temporary_directory + "/htdocs"):
        for site in drupal.sites:
            local('mysqldump --single-transaction --user=%s --password=%s --host=%s %s > %s.sql' % \
              (
                pipes.quote(site.database.username),
                pipes.quote(site.database.password),
                pipes.quote(site.database.hostname),
                pipes.quote(site.database.name),
                pipes.quote(site.database.name),
              )    
            )

def _make_archive(directory):
    file = directory + ".tar.gz"
    with cd(directory):
      local('tar czf %s htdocs' % file)
    print('Archived to %s' % file)
    return file
