import os
import sys
import tempfile

from fabric.api import *
import MySQLdb

import pantheon

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

            platform = get_drupal_platform(env_path)
            drupal_version = get_drupal_version(env_path)

            # python -> json -> php boolean disagreements. Just use int.
            drupal_update = int(latest_drupal_version != drupal_version)

            # Pantheon log only makes sense if already using Pressflow/Pantheon
            # If using Drupal, the log would show every pressflow commit ever.
            if platform == 'PANTHEON' or platform == 'PRESSFLOW':
                pantheon_log = local('git log refs/heads/%s' % project + \
                                     '..refs/remotes/origin/master'
                                    ).rstrip('\n')
            else:
                pantheon_log = 'Upgrade to Pressflow/Pantheon'

            # NOTE: Removed reporting back with log entries, so using logs
            # to determine if there is an update is a little silly. However,
            # we may want to send back logs someday, so leaving for now.

            # If log is impty, no updates.
            pantheon_update = int(bool(pantheon_log))

            status[env] = {'drupal_update': drupal_update,
                           'pantheon_update': pantheon_update,
                           'current': {'platform': platform,
                                       'drupal_version': drupal_version},
                           'available': {'drupal_version': latest_drupal_version,}}
    return status

def get_drupal_platform(drupal_root):
    #TODO: Make sure this is D7 friendly once Pressflow setup is finalized.
    return ((local("awk \"/\'info\' =>/\" " + \
            os.path.join(drupal_root, 'modules/system/system.module') + \
            r' | grep "Powered" | sed "s_^.*Powered by \([a-zA-Z]*\).*_\1_"')
            ).rstrip('\n').upper())

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

def _parse_changelog(changelog):
    """Parse a diff file and return a string of any lines added.
    changelog: string of diff style output.

    """
    #TODO: Temporary until we can get this information from a drupal git repo.

    # Parse the diff of the changelog. Only keep lines that were added.
    log = [line[1:] for line in changelog.split('\n') if (line[0:1] == '+' and
                                                          line[0:3] not in
                                                          ['+++', '+//'])]
    # Remove information about Drupal 5 updates. 
    ret = list()
    remove = False
    for line in log:
        if line[0:8] == 'Drupal 6':
            remove = False
        elif line[0:8] == 'Drupal 5':
            ret.append('')
            remove = True
        if not remove:
            ret.append(line)
    return '\n'.join(ret)

