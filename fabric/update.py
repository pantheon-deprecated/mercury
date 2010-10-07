# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
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
       with cd('/var/git/projects/pantheon'):
              local('git checkout master')
              local('git pull')
       with cd('/var/www/%s/dev' % project):
              with settings(warn_only=True):
                     pull = local('git pull origin master', capture=False)
                     if pull.failed:
                            print(pull)
                            abort('Please review the above error message and fix')
              local('git push')

def update_code(project, environment, tag=None, message=None):
    """ Update the working-tree for project/environment.

    """
    if not tag:
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not message:
        message = 'Tagging as %s for release.' % tag

    updater = update.Updater(project, environment)
    updater.code_update(tag, message)
    updater.permissions_update()

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

def git_diff(project, environment, revision_1, revision_2=''):
    """Return git diff

    """ 
    updater = update.Updater(project, environment)
    if not rev_2:
           updater.run_command('git diff $s %s' % (revision_1, revision_2))
    else:
            updater.run_command('git diff $s %s' % revision_1)

def git_status(project, environment):
    """Return git status

    """ 
    updater = update.Updater(project, environment)
    updater.run_command('git status')

