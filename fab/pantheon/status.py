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
    """Return whether or not there's a core update available.
    This will post back directly rather than using a post-build action.

    """
    drushrc = project +'_dev';
    status = local("drush @%s -n -p upc" % drushrc).rstrip().split('\n')

    postback.write_build_data('drupal_update_status', {'status': status})

