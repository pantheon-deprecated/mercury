# vim: tabstop=4 shiftwidth=4 softtabstop=4
import datetime
import tempfile
import time
import os
import traceback
import string

from pantheon import jenkinstools
from pantheon import logger
from pantheon import pantheon
from pantheon import postback
from pantheon import status
from pantheon import update
from optparse import OptionParser

from fabric.api import *

log = logger.logging.getLogger('update')

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, description="Update pantheon code and server configurations.")
    parser.add_option('-p', '--postback', dest="postback", action="store_true", default=False, help='Postback to atlas.')
    (options, args) = parser.parse_args()

    update_pantheon(options.postback)

def update_pantheon(first_boot=False):
    """Update pantheon code and server configurations.

    first_boot: bool. If this is being called from the configure job. If it
    is the first boot, we don't need to wait for jenkins or send back update
    data.

    Otherwise:

    This script is run from a cron job because it may update Jenkins (and
    therefor cannot be run inside jenkins.)

    """
    log = logger.logging.getLogger('update.pantheon')
    try:
        try:
            log.debug('Putting jenkins into quietDown mode.')
            pantheon.jenkins_quiet()
            log.debug('Checking which branch to use.')
            branch = 'master'
            if os.path.exists('/opt/branch.txt'):
                branch = open('/opt/branch.txt').read().strip() or 'master'
            log.debug('Using branch %s.' %s branch)
            log.debug('Updating from repo.')
            with cd('/opt/pantheon'):
                local('git fetch --prune origin', capture=False)
                local('git checkout --force %s' % branch, capture=False)
                local('git reset --hard origin/%s' % branch, capture=False)
            log.debug('Updating bcfg2.')
            local('/usr/sbin/bcfg2 -vqed', capture=False)
        except:
            log.exception('FATAL: Unhandled exception')
        finally:
            log.debug('Waiting for jenkins to respond.')
            for x in range(12):
                if pantheon.jenkins_running():
                    break
                else:
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 2 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.debug('Restarting jenkins.')
            pantheon.jenkins_restart()

        # If this is not the first boot, send back update data.
        if not first_boot:
            """
            We have to check for both queued jobs then the jenkins restart.
            This is because jobs could have been queued before the update
            was started, and a check on 'jenkins_running' would return True
            because the restart hasn't occured yet (safeRestart). This way,
            we first make sure the queue is 0 or jenkins is unreachable, then
            wait until it is back up.

            """
            log.debug('Not first boot, recording update data.')
            log.debug('Waiting for queued jobs to finish.')
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
                    time.sleep(5)
            # wait for jenkins to restart.
            log.debug('Waiting for jenkins to respond.')
            for x in range(30):
                if pantheon.jenkins_running():
                    break
                else:
                    time.sleep(10)
            else:
                log.error("ABORTING: Jenkins hasn't responded after 5 minutes.")
                raise Exception("ABORTING: Jenkins not responding.")
            log.info('Update completed successfully.')
    except:
        log.exception('Update encountered unrecoverable errors.')
        raise

def update_site_core(project='pantheon', keep=None):
    """Update Drupal core (from Drupal or Pressflow, to latest Pressflow).
       keep: Option when merge fails:
             'ours': Keep local changes when there are conflicts.
             'theirs': Keep upstream changes when there are conflicts.
             'force': Leave failed merge in working-tree (manual resolve).
             None: Reset to ORIG_HEAD if merge fails.
    """
    updater = update.Updater(project, 'dev')
    try:
        result = updater.core_update(keep)
        updater.drupal_updatedb()
        updater.permissions_update()
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'UpdateCore')
        raise
    else:
        jenkinstools.junit_pass('Update successful.', 'UpdateCore')

    postback.write_build_data('update_site_core', result)

    if result['merge'] == 'success':
        # Send drupal version information.
        status.drupal_update_status(project)
        status.git_repo_status(project)

def update_code(project, environment, tag=None, message=None):
    """ Update the working-tree for project/environment.

    """
    if not tag:
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not message:
        message = 'Tagging as %s for release.' % tag

    updater = update.Updater(project, environment)
    try:
        updater.test_tag(tag)
        updater.code_update(tag, message)
        updater.drupal_updatedb()
        updater.permissions_update()
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'UpdateCode')
        raise
    else:
        jenkinstools.junit_pass('Update successful.', 'UpdateCode')

    # Send back repo status and drupal update status
    status.git_repo_status(project)
    status.drupal_update_status(project)

def rebuild_environment(project, environment):
    """Rebuild the project/environment with files and data from 'live'.

    """
    updater = update.Updater(project, environment)
    try:
        updater.files_update('live')
        updater.data_update('live')
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'RebuildEnv')
        raise
    else:
        jenkinstools.junit_pass('Rebuild successful.', 'RebuildEnv')

def update_data(project, environment, source_env, updatedb='True'):
    """Update the data in project/environment using data from source_env.

    """
    updater = update.Updater(project, environment)
    try:
        updater.data_update(source_env)
        # updatedb is passed in as a string so we have to evaluate it
        if eval(string.capitalize(updatedb)):
            updater.drupal_updatedb()
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'UpdateData')
        raise
    else:
        jenkinstools.junit_pass('Update successful.', 'UpdateData')

    # The server has a 2min delay before updates to the index are processed
    with settings(warn_only=True):
        result = local("drush @%s_%s -b solr-reindex" % (project, environment))
        pantheon.log_drush_backend(result)
        result = local("drush @%s_%s -b cron" % (project, environment))
        pantheon.log_drush_backend(result)

def update_files(project, environment, source_env):
    """Update the files in project/environment using files from source_env.

    """
    updater = update.Updater(project, environment)
    try:
        updater.files_update(source_env)
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'UpdateFiles')
        raise
    else:
        jenkinstools.junit_pass('Update successful.', 'UpdateFiles')

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
    try:
        updater.run_command('git status')
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'GitStatus')
        raise
    else:
        jenkinstools.junit_pass('', 'GitStatus')

if __name__ == '__main__':
    main()
