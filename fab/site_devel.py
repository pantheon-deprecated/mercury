import os
import string

from pantheon import backup
from pantheon import ygg

def create_dev_archive(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)

    # Only create archive of development environment data.
    archive.get_dev_files()
    archive.get_dev_data()
    archive.get_dev_code(user, host)

    # Create a drushrc aliases file.
    destination = os.path.join(archive.backup_dir,'%s.aliases.drushrc.php' % project)
    get_remote_drushrc(project, user, destination)

    # Create the tarball and move to final location.
    archive.finalize()

def get_dev_files(archive_name, project):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_files()
    archive.finalize()

def get_dev_data(archive_name, project):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_data()
    archive.finalize()

def get_dev_code(archive_name, project, user):
    #TODO: For now host == project. This may change.
    host = project
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_code(user, host)
    archive.finalize()

def get_remote_drushrc(project, user, destination):
    config = ygg.get_config()[project]
    host = '%s.gotpantheon.com' % project
    environments = set(config['environments'].keys())

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

