import os
import sys
import tempfile

from fabric.api import *
import MySQLdb

import pantheon

def updatedb(alias):
    with settings(warn_only=True):
        result = local('drush %s -by updb' % alias)
    return result

def get_drupal_update_status(project):
    """Return dictionary of Drupal/Pressflow version/update information.
    project: Name of project.

    """
    repo_path = os.path.join('/var/git/projects', project)
    project_path = os.path.join(pantheon.PantheonServer().webroot, project)
    environments = pantheon.get_environments()
    status = dict()

    with cd(repo_path):
        # Get upstream updates.
        local('git fetch origin')
        # Determine latest upstream version.
        latest_drupal_version = _get_latest_drupal_version()

    for env in environments:
        env_path = os.path.join(project_path, env)

        with cd(env_path):
            local('git fetch origin')

            drupal_version = get_drupal_version(env_path)

            # python -> json -> php boolean disagreements. Just use int.
            drupal_update = int(latest_drupal_version != drupal_version)

            # Determine if there have been any new commits.
            # NOTE: Removed reporting back with log entries, so using logs
            # to determine if there is an update is a little silly. However,
            # we may want to send back logs someday, so leaving for now.
            pantheon_log = local('git log refs/heads/%s' % project + \
                                 '..refs/remotes/origin/master').rstrip('\n')

            # If log is impty, no updates.
            pantheon_update = int(bool(pantheon_log))

            #TODO: remove the reference to platform once Atlas no longer uses it.
            status[env] = {'drupal_update': drupal_update,
                           'pantheon_update': pantheon_update,
                           'current': {'platform': 'DRUPAL',
                                       'drupal_version': drupal_version},
                           'available': {'drupal_version': latest_drupal_version,}}
    return status

def get_drupal_version(drupal_root):
    """Return the current drupal version.

    """
    # Drupal 6 uses system.module, drupal 7 uses bootstrap.inc
    locations = [os.path.join(drupal_root, 'modules/system/system.module'),
                 os.path.join(drupal_root, 'includes/bootstrap.inc')]

    version = None
    for location in locations:
        version = _parse_drupal_version(location)
        if version:
            break
    return version

def _get_latest_drupal_version():
    """Check master (upstream) files to determine newest drupal version.

    """
    locations = ['modules/system/system.module',
                 'includes/bootstrap.inc']
    version = None
    for location in locations:
        contents = local('git cat-file blob refs/heads/master:%s' % location)
        temp_file = tempfile.mkstemp()[1]
        with open(temp_file, 'w') as f:
            f.write(contents)
        version = _parse_drupal_version(temp_file)
        local('rm -f %s' % temp_file)
        if version:
            break
    return version

def _parse_drupal_version(location):
    """Parse file at location to determine the Drupal version.
    location: full path to file to parse.

    """
    version = local("awk \"/define\(\'VERSION\'/\" " + location + \
                 " | sed \"s_^.*'\([6,7]\{1\}\)\.\([0-9]\{1,2\}\).*_\\1-\\2_\""
                 ).rstrip('\n')
    if len(version) > 1 and version[0:1] in ['6', '7']:
        return version
    return None

