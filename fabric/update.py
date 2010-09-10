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
       local('/usr/sbin/bcfg2 -vq', capture=False)
       print("Pantheon Updated")

def update_pressflow(project=None, environment=None):
       server = pantheon.PantheonServer()

       print ("Updating Pressflow")
       if (project == None):
              print("No project selected. Using 'pantheon'")
              project = 'pantheon'
       if (environment == None):
              print("No environment selected. Using 'dev'")
              environment = 'dev'
       with cd(server.webroot + project + '/' + environment):
              local('git pull git://gitorious.org/pantheon/6.git')
              with settings(warn_only=True):
                     local('git commit -m "updates from the Pantheon gitorious project"')
       update_permissions('%s' % (server.webroot + project + '/' + environment + '/'), server)
       print("Pressflow Updated")

def update_data(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()
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

       source_location = server.webroot + source_project + '/' + source_environment + "/"
       target_location = server.webroot + target_project + '/' + target_environment + "/"

       print('Exporting ' + source_project + '/' + source_environment + ' database to temporary directory %s' % source_temporary_directory)
       sites = pantheon.export_data(source_location, source_temporary_directory)
       print('Exporting ' + target_project + '/' + target_environment + ' database to temporary directory %s' % target_temporary_directory)
       pantheon.export_data(target_location, target_temporary_directory)

       # NOTE: Name changes should be done outside the import function (no logic, just import).
       #       Added the below as a temporary stop-gap until the TODO is fixed.
       for site in sites:
           site.database.name = target_project + "_" + target_environment

       # TODO: update process needs to be multi-site friendly. Can't use project_environment (e.g. pantheon_dev) for database name.
       #       instead we should use project_environment_sitename (e.g. pantheon_dev_getpantheon_com for sites/getpantheon.com)
       #       this namespacing will allow multi-codebase & multi-site installs. Once supported, can use:
       #       project + "_" + environment + "_" + site.get_safe_name()

       pantheon.import_data(sites)
       print(target_project + '/' + target_environment + ' database updated with database from ' + source_project + '/' + source_environment)

def update_code(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()

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

       source_location = server.webroot + source_project + '/' + source_environment + "/"
       target_location = server.webroot + target_project + '/' + target_environment + "/"

       #commit any changes in source dir:
       if os.path.exists(source_location + '.git'):
              with cd(source_location):
                     with settings(warn_only=True):
                            local('git add -A .')
                            local('git commit -av -m "committing found changes"')
                     branch = local('git branch | grep "*"').lstrip('* ').rstrip('\n')
                     if branch != 'master':
                            print("current source git branch is " + branch + " - merging into master branch")
                            with settings(warn_only=True):
                                   local('git checkout master')
                                   local('git merge ' + branch)
                                   local('git checkout ' + branch)
       else:
              abort("Source target not in version control.")

       #update target dir:
       if os.path.exists(target_location + '.git'):
              with cd(target_location):
                     local('git pull')
       else:
              with cd(source_location):
                     temporary_directory = tempfile.mkdtemp()
                     local('git archive master | sudo tar -x -C ' + temporary_directory)
                     local('rsync -av --delete --exclude=settings.php --exclude=files ' + temporary_directory + '/ ' + target_location)
                     local('rm -rf ' + temporary_directory)

       update_permissions(source_location, server)
       update_permissions(target_location, server)
       print(target_project + '/' + target_environment + ' project updated from ' + source_project + '/' + source_environment)
       
def update_files(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()

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

       local('rsync -av --delete '+ server.webroot + source_project + '/' + source_environment + '/sites/all/files ' + server.webroot + target_project + '/' + target_environment + '/sites/all/')
       local('rsync -av --delete '+ server.webroot + source_project + '/' + source_environment + '/sites/default/files ' + server.webroot + target_project + '/' + target_environment + '/sites/default/')
       print(target_project + '/' + target_environment + ' files updated from ' + source_project + '/' + source_environment)

def update_permissions(dir, server):
       with cd(dir):
              local('chown -R root:' + server.group + ' *')
              local('chown ' + server.group + ':' + server.group + ' sites/default/settings.php')
              local('chmod 660 sites/default/settings.php')
              local('find . -type d -exec chmod 755 {} \;')
              local('find sites/*/files -type d -exec chmod 775 {} \;')
              local('find sites/*/files -type f -exec chmod 660 {} \;')

