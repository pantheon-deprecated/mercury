from pantheon import pantheon
from pantheon import ygg

from fabric.api import *

def main():
    upgrade_drush()

def create_aliases():
    config = ygg.get_config()
    server = pantheon.PantheonServer()
    project = str(config.keys()[0])
    config = config[project]
    environments = set(config['environments'].keys())
    for env in environments:
        drush_dict = {'project': project,
                      'environment': env,
                      'root': config['environments'][env]['apache']['DocumentRoot']}
        server.create_drush_alias(drush_dict)

def upgrade_drush():
    """Git clone Drush and download Drush-Make.

    """
    with cd('/opt'):
        local('[ ! -d drush ] || rm -rf drush')
        #local('wget http://ftp.drupal.org/files/projects/drush-6.x-3.3.tar.gz')
        #local('tar xvzf drush-6.x-3.3.tar.gz')
        #local('rm -f drush-6.x-3.3.tar.gz')
        local('git clone --branch 7.x-4.x http://git.drupal.org/project/drush.git')
        local('chmod 555 drush/drush')
        local('chown -R root: drush')
        local('mkdir /opt/drush/aliases')
        local('ln -sf /opt/drush/drush /usr/local/bin/drush')
        local('drush dl drush_make')
    create_aliases()

if __name__ == '__main__':
    main()
