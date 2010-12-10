import drupaltools
import gittools
import postback

from fabric.api import *

def git_repo_status(project):
    """Post back to Atlas with the status of the project Repo.

    """
    repo = gittools.GitRepo(project)
    status = repo.get_repo_status()

    postback.write_build_data('git_repo_status', {'status': status})

def drupal_update_status(project):
    """Return drupal/pantheon update status for each environment.

    """
    status = drupaltools.get_drupal_update_status(project)

    postback.write_build_data('drupal_core_status', {'status': status})


