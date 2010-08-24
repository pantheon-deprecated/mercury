# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import tempfile
import os

import pantheon


def update_pantheon():
       print("Updating Pantheon from Launchpad")
       local('/etc/init.d/bcfg2-server stop')
       local('cd /opt/pantheon; bzr up')
       pantheon.restart_bcfg2()
       local('/usr/sbin/bcfg2 -vq')
       print("Pantheon Updated")

def update_pressflow(project=None, environment=None):
       webroot = pantheon.PantheonServer().webroot 
       
       print ("Updating Pressflow")
       if (project == None):
              print("No project selected. Using 'pantheon'")
              project = 'pantheon'
       if (environment == None):
              print("No environment selected. Using 'dev'")
              environment = 'dev'
       with cd(webroot + project + '_' + environment):
              local('git pull --rebase git://gitorious.org/pantheon-pressflow/pantheon-pressflow.git')
              update_permissions('%s' % (webroot + project + '_' + environment))
              with settings(warn_only=True):
                     local('git commit -m "updates from the Pantheon gitorious project"')
       print("Pressflow Updated")

def update_data(source_project=None, source_environment=None, target_project=None, target_environment=None):
       webroot = pantheon.PantheonServer().webroot
       source_temporary_directory = tempfile.mkdtemp()
       target_temporary_directory = tempfile.mkdtemp()

       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'live'")
              source_environment = 'live'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       source_location = webroot + source_project + '_' + source_environment + "/"
       target_location = webroot + target_project + '_' + target_environment + "/"
       print('Exporting ' + source_project + '/' + source_environment + ' database to temporary directory %s' % source_temporary_directory)
       sites = pantheon.export_data(source_location, source_temporary_directory)
       print('Exporting ' + target_project + '/' + target_environment + ' database to temporary directory %s' % target_temporary_directory)
       pantheon.export_data(target_location, target_temporary_directory)
       pantheon.import_data(sites, target_project, target_environment)
       print(target_project + '_' + target_environment + ' database updated with database from ' + source_project + '_' + source_environment)

def update_code(source_project=None, source_environment=None, target_project=None, target_environment=None):
       webroot = pantheon.PantheonServer().webroot
       
       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'dev'")
              source_environment = 'dev'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       #todo: add test for uncommitted code in source_environment
       source_location = webroot + source_project + '_' + source_environment + "/"
       target_location = webroot + target_project + '_' + target_environment + "/"

       if not os.path.exists(source_location + '.git'):
              abort("Source target not in version control.")

       if os.path.exists(target_location + '.git'):
              with cd(target_location):
                     local('git pull')
       else:
              with cd(source_location):
                     temporary_directory = tempfile.mkdtemp()
                     local('git archive master | sudo tar -x -C ' + temporary_directory)
                     local('rsync -av --exclude=settings.php ' + temporary_directory + '/* ' + target_location)
                     local('rm -rf temporary_directory')

       update_permissions(target_location)

       print(target_project + '_' + target_environment + ' project updated from ' + source_project + '_' + source_environment)
       
def update_files(source_project=None, source_environment=None, target_project=None, target_environment=None):
       webroot = pantheon.PantheonServer().webroot
       
       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'live'")
              source_environment = 'live'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       local('rsync -av '+ webroot + source_project + '_' + source_environment + '/sites/all/files ' + webroot + target_project + '_' + target_environment + '/sites/all/')
       print(target_project + '_' + target_environment + ' files updated from ' + source_project + '_' + source_environment)

def update_permissions(dir):
       with cd(dir):
              local('chown -R root:www-data *')
              local('chown www-data:www-data sites/default/settings.php')
              local('chmod 660 sites/default/settings.php')
              local('find . -type d -exec chmod 755 {} \;')
              local('chmod 775 sites/*/files')
