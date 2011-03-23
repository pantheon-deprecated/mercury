import drupaltools
import gittools
import postback
import logger

from fabric.api import *

def git_repo_status(project):
    """Post back to Atlas with the status of the project Repo.

    """
    log = logger.logging.getLogger('pantheon.status.repo')
    log.info('Updating status of the projects repository.')
    try:
        repo = gittools.GitRepo(project)
        status = repo.get_repo_status()
    except:
        log.exception('Repository status update unsuccessful.')
        raise
    else:
        log.info('Project repository status updated.')
        postback.write_build_data('git_repo_status', {'status': status})

def drupal_update_status(project):
    """Return drupal/pantheon update status for each environment.

    """
    log = logger.logging.getLogger('pantheon.status.environments')
    log.info('Updating status of the drupal environments.')
    try:
        status = drupaltools.get_drupal_update_status(project)
    except:
        log.exception('Environments status update unsuccessful.')
        raise
    else:
        log.info('Drupal environment status updated.')
        postback.write_build_data('drupal_core_status', {'status': status})


