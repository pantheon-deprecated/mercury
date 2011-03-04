import os
import string

from pantheon import backup
from pantheon import ygg

def create_dev_archive(name, project, user):
    archive = backup.PantheonBackup(name, project)

    # Only create archive of development environment data.
    archive.environments = ['dev']
    archive.backup_files()
    archive.backup_data(dest='dev_database.sql')

    # Create a drushrc aliases file.
    destination = os.path.join(archive.backup_dir,'%s.aliases.drushrc.php' % project)
    create_remote_drushrc(project, user, destination)

    archive.finalize()

def create_remote_drushrc(project, user, destination):
    config = ygg.get_config()[project]
    host = '%s.gotpantheon.com' % project
    environments = set(config['environments'].keys())

    # Build the environment specific aliases
    env_aliases = ''
    template = string.Template(_get_env_alias())
    for env in environments:
        values = {'env': env,
                  'root': '/var/www/%s/%s' % (project, env)}
        env_aliases += template.safe_substitute(values)

    # Build the final alias file (using the environment aliases).
    template = string.Template(_get_server_alias())
    values = {'host': host,
              'user': user,
              'env_aliases': env_aliases}
    with open(destination, 'w') as f:
        f.write(template.safe_substitute(values))

def _get_server_alias():
    return """
<?php

$aliases['server'] = array(
  'remote-host' => '${host}',
  'remote-user' => '${user}',
  'uri' => 'default',
);
${env_aliases}
?>
"""

def _get_env_alias():
    return """
$aliases['${env}'] = array(
  'parent' => '@server',
  'root' => '${root}',
);
"""

