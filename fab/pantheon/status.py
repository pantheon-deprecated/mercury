import traceback

import drupaltools
import gittools
import postback
import jenkinstools

from fabric.api import *

def git_repo_status(project):
    """Post back to Atlas with the status of the project Repo.

    """
    try:
        repo = gittools.GitRepo(project)
        status = repo.get_repo_status()
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'GitRepoStatus')
        raise
    else:
        jenkinstools.junit_pass('%s' % status, 'GitRepoStatus')
        postback.write_build_data('git_repo_status', {'status': status})

def drupal_update_status(project):
    """Return drupal/pantheon update status for each environment.

    """
    try:
        status = drupaltools.get_drupal_update_status(project)
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'UpdateStatus')
        raise
    else:
        jenkinstools.junit_pass('%s' % status, 'UpdateStatus')
        postback.write_build_data('drupal_core_status', {'status': status})


