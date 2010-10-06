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
       with cd('/var/git/projects/pantheon'):
              local('git checkout master')
              local('git pull')
       with cd('/var/www/pantheon/dev'):
              with settings(warn_only=True):
                     pull = local('git pull origin master', capture=False)
                     if pull.failed:
                            print(pull)
                            abort('Please review the above error message and fix')
              local('git push')

def update_test_code(tag=None, message=None):
       if not tag:
              print("No tag name provided. Using 'date stamp'")
              tag = local('date +%Y%m%d%H%M%S').rstrip('\n')
       if not message:
              print("No message provided. Using default")
              message  = 'tagging current state of /var/www/pantheon/dev'
       with cd('/var/www/pantheon/dev'):
              local("git tag '%s' -m '%s'" % (tag, message))
              local('git push')
              local('git push --tags')
       with cd('/var/www/pantheon/test'):
              local('git fetch -t')
              local("git reset --hard '%s'" % (tag))

def update_live_code():
       #get current tag from test branch:
       with cd('/var/www/pantheon/test'):
              tag = local('git describe').rstrip('\n')
       with cd('/var/www/pantheon/live'):
              local('git fetch -t')
              local("git reset --hard '%s'" % (tag))

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
