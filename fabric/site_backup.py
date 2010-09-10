# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import tempfile

import pantheon

def backup_site(export_name, project='pantheon', environment='dev', export_to=None):
    temporary_directory = tempfile.mkdtemp()
    server = pantheon.PantheonServer()

    #TODO: change _ to / when we update the vhosts
    location = server.webroot + project + '/' + environment + "/"

    print('Exporting to temporary directory %s' % temporary_directory)
    _export_files(location, temporary_directory)
    pantheon.export_data(location, temporary_directory + '/htdocs')
    archive = _make_archive(temporary_directory, export_name)
    
    if not export_to:
        export_to = server.ftproot
    local("mv %s/%s %s" % (temporary_directory, archive, export_to))
    local("rm -rf %s" % (temporary_directory))
        
    print "Exported to: " + export_to

def _export_files(webroot, temporary_directory):
    local('cp -R %s %s/htdocs' % (webroot, temporary_directory))

def _make_archive(directory, name):
    file = name + ".tar.gz"
    with cd(directory):
      local('tar czf %s htdocs' % file)
    return file
