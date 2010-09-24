# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import tempfile
import os

from pantheon import pantheon


def update_pantheon():
       print("Updating Pantheon from Launchpad")
       local('/etc/init.d/bcfg2-server stop')
       local('cd /opt/pantheon; bzr up')
       pantheon.restart_bcfg2()
       local('/usr/sbin/bcfg2 -vq', capture=False)
       print("Pantheon Updated")

def update_pressflow(git_dir=None,branch=None):
       if (git_dir == None):
              print("No dir selected. Using '/var/git/projects'")
              git_dir = '/var/git/projects'
       if (branch == None):
              print("No branch selected. Using 'master'")
              branch = 'master'

       with cd(git_dir):
              with settings(warn_only=True):
                     response = local('git branch | grep ' + branch, capture=False)
                     if response.failed:
                            abort('Branch ' + branch + ' does not exist')
              
              orig_branch = local('git branch | grep "*"').lstrip('* ').rstrip('\n')
              local('git checkout ' + branch)
              with settings(warn_only=True):
                      status = local('git status | grep "nothing to commit"', capture=False)
                      if status.failed:
                             local('git add -A .')
                             local('git commit -av -m "committing found changes"')

              if (branch == 'master'):
                     local('git pull')
              else:
                     local('git checkout ' + branch)
                     local('git merge master')
              
              local('git checkout ' +  orig_branch)
       print(branch + ' branch of ' + git_dir + ' Updated')

def update_project_code(project=None,  environment=None):
       server = pantheon.PantheonServer()

       if (project == None):
              print("No project selected. Using 'pantheon'")
              project = 'pantheon'
       if (environment == None):
              print("No environment selected. Using 'dev'")
              environment = 'dev'

       location = server.webroot + project + '/' + environment + "/"

       #push to repo:
       with cd(location):
              local('git checkout %s' % project)
              with settings(warn_only=True):
                     status = local('git status | grep "nothing to commit"', capture=False)
                     if status.failed:
                            local('git add -A .')
                            local("git commit -m 'Initialize Project: %s'" % project)
                            local('git tag %s.initialization' % project)
                            local('git push')
                            local('git push --tags')
                            
       print(project + 'project updated with code from ' + location)

def update_env_code(project=None, environment=None):
       server = pantheon.PantheonServer()

       if (project == None):
              print("No project selected. Using 'pantheon'")
              project = 'pantheon'
       if (environment == None):
              print("No environment selected. Using 'dev'")
              environment = 'dev'

       location = server.webroot + project + '/' + environment + "/"
       
       #pull from repo:
       with cd(location):
              local('git checkout %s' % project)
              local('git pull')

       #check permissions:
       update_permissions(location, server)

       print(location + 'updated with code from project' + project)
       
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
              local('chown -R root:' + server.web_group + ' *')
              local('chown ' + server.web_group + ':' + server.web_group + ' sites/default/settings.php')
              local('chmod 660 sites/default/settings.php')
              local('find . -type d -exec chmod 755 {} \;')
              local('find sites/*/files -type d -exec chmod 775 {} \;')
              local('find sites/*/files -type f -exec chmod 660 {} \;')

