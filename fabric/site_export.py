from fabric.api import *
from pantheon import PantheonServer, DrupalInstallation
from tempfile import mkdtemp
import subprocess
import pipes

def export_site(project = None ,environment = None):
    temporary_directory = mkdtemp()
    webroot = PantheonServer().webroot

    if (project == None):
        print("No project set. Using 'pantheon'")
        project = 'pantheon'
    if (environment == None):
        print("No environment set. Using 'live' environment")
        environment = 'live'

    #TODO: change _ to / when we update the vhosts
    location = webroot + project + '_' + environment + "/"

    print('Exporting to temporary directory %s' % temporary_directory)
    _export_files(location, temporary_directory)
    _export_data(location, temporary_directory)
    _make_archive(temporary_directory)

def _export_files(webroot, temporary_directory):
    local('git clone %s %s/htdocs' % (webroot, temporary_directory))
    local('rm -rf %s/htdocs/.git' % temporary_directory)

def _export_data(webroot, temporary_directory):
    sites = DrupalInstallation(webroot).get_sites()
    with cd(temporary_directory + "/htdocs"):
        exported = list()
        for site in sites:
            if site.valid:
                # If multiple sites use same db, only export once.
                if site.database.name not in exported:
                    local("mysqldump --single-transaction --user='%s' --password='%s' --host='%s' %s > %s.sql" % \
                      ( site.database.username, 
                        site.database.password, 
                        site.database.hostname, 
                        site.database.name,
                        site.database.name,
                      )    
                    )
                    exported.append(site.database.name)

def _make_archive(directory):
    file = directory + ".tar.gz"
    with cd(directory):
      local('tar czf %s htdocs' % file)
    print('Archived to %s' % file)
    return file
