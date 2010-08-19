# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import tempfile

from pantheon import *


def export_site(project = None ,environment = None):
    temporary_directory = tempfile.mkdtemp()
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
    Pantheon.export_data(location + '/htdocs', temporary_directory)
    _make_archive(temporary_directory)

def _export_files(webroot, temporary_directory):
    local('cp -R %s %s/htdocs' % (webroot, temporary_directory))

def _make_archive(directory):
    file = directory + ".tar.gz"
    with cd(directory):
      local('tar czf %s htdocs' % file)
    print('Archived to %s' % file)
    return file
