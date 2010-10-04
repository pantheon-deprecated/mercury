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

def update_pressflow():
       with cd('/var/git/projects'):
              local('git checkout master')
              local('git pull')
       with cd('/var/www/pantheon/dev'):
              local('git checkout master')
              local('git pull')
              local('git checkout pantheon')
              local('git merge master')
              local('git push')

def update_test_code(tag=None):
       if (tag == None):
              print("No tag name provided. Using 'date stamp'")
              tag = local('date +%Y%m%d%H%M%S').rstrip('\n')
       with cd('/var/www/pantheon/dev'):
              local('git tag ' + tag + ' -m "tagging current state of /var/www/pantheon/dev"')
              local('git push')
              local('git push --tags')
       with cd('/var/www/pantheon/test'):
              local('git fetch -t')
              local('git reset --hard ' + tag)

def update_live_code():
       #get current tag from test branch
       with cd('/var/www/pantheon/test'):
              tag = local('git describe').rstrip('\n')
       with cd('/var/www/pantheon/live'):
              local('git fetch -t')
              local('git reset --hard ' + tag)

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

       print('Exporting ' + source_project + '/' + source_environment + ' database to temporary directory %s' % source_temporary_directory)
       dump_file = pantheon.export_data(source_project, source_environment, source_temporary_directory)
       print('Exporting ' + target_project + '/' + target_environment + ' database to temporary directory %s' % target_temporary_directory)
       pantheon.export_data(target_project, target_environment, target_temporary_directory)

       pantheon.import_data(target_project, target_environment, dump_file)
       local('rm -rf ' + temp_dir)
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

def get_branch(dir):
       with cd(dir):
              branches = local('git branch').lstrip('* ').split()
              if branches.count == 1:
                     return branches
              else:
                     branches.remove('master')
                     if branches.count == 1:
                            return branches
                     else:
                            return local('git branch | grep "*"').lstrip('* ').rstrip('\n')

def does_branch_exist(dir,branch):
       with cd(dir):
              with settings(warn_only=True):
                     response = local('git branch | grep ' + branch, capture=False)
                     if response.failed:
                            abort('Branch ' + branch + ' does not exist in ' + dir)

def commit_if_needed(dir,branch):
       with cd(dir):
              with settings(warn_only=True):
                     local('git checkout ' + branch)
                     status = local('git status | grep "nothing to commit"', capture=False)
                     if status.failed:
                            local('git add -A .')
                            local('git commit -av -m "committing found changes"')
              print(local('git status'))
 
def push_upstream(dir,branch,project):
       with cd(dir):
              with settings(warn_only=True):
                     local('git checkout ' + branch)
                     #datestamp = 
                     local('git tag %s' % project.datestamp)
                     local('git push --tags')
                     
def pull_downstream(dir,branch):
       with cd(dir):
              if (branch == 'master'):
                     local('git pull')
              else:
                     with settings(warn_only=True):
                            response = local('git branch | grep master', capture=False)
                     if response.failed:
                            local('git fetch')
                            local('git reset --hard')
                     else:
                            local('git checkout ' + branch)
                            local('git merge master')
