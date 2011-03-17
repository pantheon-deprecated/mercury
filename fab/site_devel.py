import os
import string

from pantheon import backup
from pantheon import pantheon

DESTINATION = '/srv/dev_downloads'

def get_dev_downloads(resource, archive_name, project, user=None):
    """Wapper method for a Jenkins job to get development resources.
    resource: type of download you want (all/files/data/code/drushrc)
    archive_name: resulting name of archive.
    project: project name
    user: user that has ssh access to box.

    """
    if resource == 'all':
        print "Creating archive of all dev resources."
        _dev_all(archive_name, project, user)
    elif resource == 'files':
        print "Creating archive of dev files."
        _dev_files(archive_name, project)
    elif resource == 'data':
        print "Creating archive of dev data."
        _dev_data(archive_name, project)
    elif resource == 'code':
        print "Creating archive of dev code."
        _dev_code(archive_name, project, user)
    elif resource == 'drushrc':
        print "Creating remote drushrc file."
        destination = os.path.join(_get_destination(),
                                   '%s.aliases.drushrc' % project)
        _dev_drushrc(project, user, destination)


def _dev_all(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)

    # Only create archive of development environment data.
    archive.get_dev_files()
    archive.get_dev_data()
    archive.get_dev_code(user, project)

    # Create a drushrc aliases file.
    destination = os.path.join(archive.backup_dir,'%s.aliases.drushrc.php' % project)
    _dev_drushrc(project, user, destination)

    # Create the tarball and move to final location.
    archive.finalize(_get_destination())

def _dev_files(archive_name, project):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_files()
    archive.finalize(_get_destination())

def _dev_data(archive_name, project):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_data()
    archive.finalize(_get_destination())

def _dev_code(archive_name, project, user):
    #TODO: For now host == project. This may change.
    host = project
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_code(user, host)
    archive.finalize(_get_destination())

def _dev_drushrc(project, user, destination):
    host = '%s.gotpantheon.com' % project
    environments = pantheon.get_environments()

    # Build the environment specific aliases
    env_aliases = ''
    template = string.Template(_get_env_alias())

    for env in environments:
        values = {'host': host,
                  'user': user,
                  'project': project,
                  'env': env,
                  'root': '/var/www/%s/%s' % (project, env)}
        env_aliases += template.safe_substitute(values)

    with open(destination, 'w') as f:
        f.write('<?php\n%s\n' % env_aliases)

def _get_env_alias():
    return """
$aliases['${project}_${env}'] = array(
  'remote-host' => '${host}',
  'remote-user' => '${user}',
  'uri' => 'default',
  'root' => '${root}',
);
"""

def _get_destination():
    return DESTINATION

