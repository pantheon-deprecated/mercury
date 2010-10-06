# vim: tabstop=4 shiftwidth=4 softtabstop=4
import datetime
import tempfile
import os

from pantheon import pantheon
from pantheon import update

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

def rebuild_environment(project, environment):
    """Rebuild the project/environment with files and data from 'live'.

    """
    updater = update.Updater(project, environment)
    updater.files_update('live')
    updater.data_update('live')

def update_data(project, environment, source_env):
    """Update the data in project/environment using data from source_env.

    """
    updater = update.Updater(project, environment)
    updater.data_update(source_env)

def update_files(project, environment, source_env):
    """Update the files in project/environment using files from source_env.

    """
    updater = update.Updater(project, environment)
    updater.files_update(source_env)
