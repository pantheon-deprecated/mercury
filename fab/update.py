# vim: tabstop=4 shiftwidth=4 softtabstop=4
import datetime
import tempfile
import time
import urllib2
import os
import traceback

from pantheon import hudsontools
from pantheon import pantheon
from pantheon import postback
from pantheon import status
from pantheon import update

from fabric.api import *

def update_pantheon(first_boot=False):
    """Update pantheon code and server configurations.

    first_boot: bool. If this is being called from the configure job. If it
    is the first boot, we don't need to wait for hudson or send back update
    data.

    Otherwise:

    This script is run from a cron job because it may update Hudson (and
    therefor cannot be run inside hudson.)

    If the script is successful, a known message will be printed to
    stdout which will be redirected to a log file. The hudson job
    post_update_pantheon will check this log file for the message to
    determine if it was successful.

    """
    # Put hudson into quietDown mode so no more jobs are started.
    urllib2.urlopen('http://localhost:8090/quietDown')
    # Update from repo
    with cd('/opt/pantheon'):
        local('git pull origin master', capture=False)
    # Update from BCFG2
    local('/usr/sbin/bcfg2 -vqed', capture=False)
    # Restart Hudson
    local('curl -X POST http://localhost:8090/safeRestart', capture=False)

    # If this is not the first boot, send back update data.
    if not first_boot:
        """
        We have to check for both queued jobs then the hudson restart.
        This is because jobs could have been queued before the update
        was started, and a check on 'hudson_running' would return True
        because the restart hasn't occured yet (safeRestart). This way,
        we first make sure the queue is 0 or hudson is unreachable, then
        wait until it is back up.

        """

        # wait for any jobs that were queued to finish.
        while True:
            queued = pantheon.hudson_queued()
            if queued == 0:
                # No more jobs, give hudson a few seconds to begin restart.
                time.sleep(5)
                break
            # Hudson is unreachable (already in restart process)
            elif queued == -1:
                break
            else:
                time.sleep(5)
        # wait for hudson to restart.
        while not pantheon.hudson_running():
            time.sleep(5)
        # Run post_pantheon_update hudson job
        try:
            urllib2.urlopen('http://localhost:8090/job/post_update_pantheon/build')
        except Exception as detail:
            print "Warning: Could not run post_update_pantheon job:\n%s" % detail
        # stdout is redirected in cron, so this will go to log file.
        print "UPDATE COMPLETED SUCCESSFULLY"

def post_update_pantheon():
    """Determine if cron run of panthoen_update was successful.

    """
    response = dict()
    log_path = '/tmp/pantheon_update.log'
    if os.path.isfile(log_path):
        log = local('cat %s' % log_path)
        local('rm -f %s' % log_path)
        if 'UPDATE COMPLETED SUCCESSFULLY' in log:
            response['status'] = 'SUCCESS'
            response['msg'] = ''
            hudsontools.junit_pass('', 'PostUpdate')
        else:
            response['status'] = 'FAILURE'
            response['msg'] = 'Panthoen update did not complete.'
            hudsontools.junit_fail(response['msg'], 'PostUpdate')
        print log
    else:
        response['status'] = 'FAILURE'
        response['msg'] = 'No Pantheon update log was found.'
        hudsontools.junit_fail(response['msg'], 'PostUpdate')
        print 'No update log found.'
    postback.write_build_data('update_pantheon', response)

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
        hudsontools.junit_error(traceback.format_exc(), 'UpdateCore')
        raise
    else:
        hudsontools.junit_pass('Update successful.', 'UpdateCore')

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
        hudsontools.junit_error(traceback.format_exc(), 'UpdateCode')
        raise
    else:
        hudsontools.junit_pass('Update successful.', 'UpdateCode')

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
        hudsontools.junit_error(traceback.format_exc(), 'RebuildEnv')
        raise
    else:
        hudsontools.junit_pass('Rebuild successful.', 'RebuildEnv')

def update_data(project, environment, source_env):
    """Update the data in project/environment using data from source_env.

    """
    updater = update.Updater(project, environment)
    try:
        updater.data_update(source_env)
    except:
        hudsontools.junit_error(traceback.format_exc(), 'UpdateData')
        raise
    else:
        hudsontools.junit_pass('Update successful.', 'UpdateData')

def update_files(project, environment, source_env):
    """Update the files in project/environment using files from source_env.

    """
    updater = update.Updater(project, environment)
    try:
        updater.files_update(source_env)
    except:
        hudsontools.junit_error(traceback.format_exc(), 'UpdateFiles')
        raise
    else:
        hudsontools.junit_pass('Update successful.', 'UpdateFiles')

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
        hudsontools.junit_error(traceback.format_exc(), 'GitStatus')
        raise
    else:
        hudsontools.junit_pass('', 'GitStatus')

