# vim: tabstop=4 shiftwidth=4 softtabstop=4
import datetime
import tempfile
import time
import os
import string

from pantheon import logger
from pantheon import pantheon
from pantheon import postback
from pantheon import status
from pantheon import update
from optparse import OptionParser

from fabric.api import *

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, description="Update pantheon code and server configurations.")
    parser.add_option('-p', '--postback', dest="postback", action="store_true", default=False, help='Postback to atlas.')
    parser.add_option('-d', '--debug', dest="debug", action="store_true", default=False, help='Include debug output.')
    (options, args) = parser.parse_args()
    log = logger.logging.getLogger('pantheon.update')

    if options.debug:
        log.setLevel(10)
    update_pantheon(options.postback)

def update_pantheon(postback=True):
    """Update pantheon code and server configurations.

    postback: bool. If this is being called from the configure job, then it
    is the first boot, we don't need to wait for jenkins or send back update
    data.

    Otherwise:

    This script is run from a cron job because it may update Jenkins (and
    therefor cannot be run inside jenkins.)

    """
    log = logger.logging.getLogger('pantheon.update')
    if postback:
        log.info('Initiated pantheon update.')

    try:
        # Ensure the JDK is properly installed.
        local('apt-get install -y default-jdk')
        
        # Nightly security package updates.
        # Never update openssh-server automatically.
        local('aptitude hold openssh-server openssh-client')
        local('aptitude update')
        local('aptitude safe-upgrade -o Aptitude::Delete-Unused=false --assume-yes --target-release `lsb_release -cs`-security', capture=False)
        try:
            log.debug('Putting jenkins into quietDown mode.')
            pantheon.jenkins_quiet()
            # TODO: Actually get security upgrades.
            # Get package security updates.
            #log.debug('Checking for security releases')
            #local('aptitude update')
            # Update pantheon code.
            log.debug('Checking which branch to use.')
            branch = 'master'
            if os.path.exists('/opt/branch.txt'):
                branch = open('/opt/branch.txt').read().strip() or 'master'
            log.debug('Using branch %s.' % branch)
            log.debug('Updating from repo.')
            with cd('/opt/pantheon'):
                local('git fetch --prune origin', capture=False)
                local('git checkout --force %s' % branch, capture=False)
                local('git reset --hard origin/%s' % branch, capture=False)
            # Run bcfg2.
            local('/usr/sbin/bcfg2 -vqed', capture=False)
        except:
            log.exception('Pantheon update encountered a fatal error.')
            raise
        finally:
            for x in range(12):
                if pantheon.jenkins_running():
                    break
                else:
                    log.debug('Waiting for jenkins to respond.')
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 2 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.debug('Restarting jenkins.')
            pantheon.jenkins_restart()

        # If this is not the first boot, send back update data.
        if postback:
            """
            We have to check for both queued jobs then the jenkins restart.
            This is because jobs could have been queued before the update
            was started, and a check on 'jenkins_running' would return True
            because the restart hasn't occured yet (safeRestart). This way,
            we first make sure the queue is 0 or jenkins is unreachable, then
            wait until it is back up.

            """
            log.debug('Not first boot, recording update data.')
            while True:
                queued = pantheon.jenkins_queued()
                if queued == 0:
                    # No more jobs, give jenkins a few seconds to begin restart.
                    time.sleep(5)
                    break
                # Jenkins is unreachable (already in restart process)
                elif queued == -1:
                    break
                else:
                    log.debug('Waiting for queued jobs to finish.')
                    time.sleep(5)
            # wait for jenkins to restart.
            for x in range(30):
                if pantheon.jenkins_running():
                    break
                else:
                    log.debug('Waiting for jenkins to respond.')
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 5 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.info('Pantheon update completed successfully.')
        else:
            log.info('Pantheon update completed successfully.')
    except:
        log.exception('Pantheon update encountered a fatal error.')
        raise

def update_site_core(project='pantheon', keep=None, taskid=None):
    """Update Drupal core (from Drupal or Pressflow, to latest Pressflow).
       keep: Option when merge fails:
             'ours': Keep local changes when there are conflicts.
             'theirs': Keep upstream changes when there are conflicts.
             'force': Leave failed merge in working-tree (manual resolve).
             None: Reset to ORIG_HEAD if merge fails.
    """
    updater = update.Updater(project, 'dev')
    result = updater.core_update(keep)
    if result['merge'] == 'success':
        # Send drupal version information.
        status.drupal_update_status(project)
        status.git_repo_status(project)
        updater.drupal_updatedb()
        updater.permissions_update()
        postback.write_build_data('update_site_core', result)

    else:
        log = logger.logging.getLogger('pantheon.update_site_core')
        updater.permissions_update()
        log.error('Upstream merge did not succeed. Review conflicts.')
        
        
def update_code(project, environment, tag=None, message=None, taskid=None):
    """ Update the working-tree for project/environment.

    """
    if not tag:
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not message:
        message = 'Tagging as %s for release.' % tag

    updater = update.Updater(project, environment)
    updater.test_tag(tag)
    updater.code_update(tag, message)
    updater.drupal_updatedb()
    updater.permissions_update()

    # Send back repo status and drupal update status
    status.git_repo_status(project)
    status.drupal_update_status(project)

def rebuild_environment(project, environment):
    """Rebuild the project/environment with files and data from 'live'.

    """
    updater = update.Updater(project, environment)
    updater.files_update('live')
    updater.data_update('live')

def update_data(project, environment, source_env, updatedb='True', taskid=None):
    """Update the data in project/environment using data from source_env.

    """
    updater = update.Updater(project, environment)
    updater.data_update(source_env)
    # updatedb is passed in as a string so we have to evaluate it
    if eval(string.capitalize(updatedb)):
        updater.drupal_updatedb()

    # The server has a 2min delay before updates to the index are processed
    updater.solr_reindex()
    updater.run_cron()

def update_files(project, environment, source_env, taskid=None):
    """Update the files in project/environment using files from source_env.

    """
    updater = update.Updater(project, environment)
    updater.files_update(source_env)

def git_diff(project, environment, revision_1, revision_2=None):
    """Return git diff

    """
    updater = update.Updater(project, environment)
    if not revision_2:
           updater.run_command('git diff %s' % revision_1)
    else:
           updater.run_command('git diff %s %s' % (revision_1, revision_2))

def git_status(project, environment):
    """Return git status

    """
    updater = update.Updater(project, environment)
    updater.run_command('git status')

if __name__ == '__main__':
    main()
