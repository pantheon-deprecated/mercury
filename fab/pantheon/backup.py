import os
import tempfile

from configobj import ConfigObj
from fabric.api import *

import pantheon

class PantheonBackup():

    def __init__(self, name, project):
        """Initialize Backup Object.
        name: name of backup (resulting file: name.tar.gz)
        project: name of project to backup.

        """
        self.server = pantheon.PantheonServer()
        self.project =  project
        self.working_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.working_dir, self.project)
        self.name = name + '.tar.gz'

    def backup_files(self, environments=pantheon.get_environments()):
        """Backup files for all environments (dev, test, live) of a project.

        """
        for env in environments:
            source = os.path.join(self.server.webroot, self.project, env)
            local('mkdir -p %s' % self.backup_dir)
            local('rsync -avz %s %s' % (source, self.backup_dir))

    def backup_data(self, environments=pantheon.get_environments()):
        """Backup databases for all environments (dev, test, live) of a project.

        """
        for env in environments:
            drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                               self.project, env))
            dest = os.path.join(self.backup_dir, env, 'database.sql')
            self._dump_data(dest, drupal_vars)

    def backup_repo(self):
        """Backup central repository for a project.

        """
        dest = os.path.join(self.backup_dir, '%s.git' % (self.project))
        local('rsync -avz /var/git/projects/%s/ %s' % (self.project, dest))

    def backup_config(self, version):
        """Write the backup config file.
        version: int. Backup schema version. Used to maintain backward
                 compatibility as backup formats could change.

        """
        config_file = os.path.join(self.backup_dir, 'pantheon.backup')
        config = ConfigObj(config_file)
        config['backup_version'] = version
        config['project'] = self.project
        config.write()

    def make_archive(self):
        """Tar/gzip the files to be backed up.

        """
        with cd(self.working_dir):
            local('tar czf %s %s' % (self.name, self.project))

    def move_archive(self):
        """Move archive from temporary working dir to ftp dir.

        """
        with cd(self.working_dir):
            local('mv %s %s' % (self.name, self.server.ftproot))

    def cleanup(self):
        """ Remove working_dir """
        local('rm -rf %s' % self.working_dir)

    def _dump_data(self, destination, db_dict):
        """Dump a database to a .sql file.
        destination: Full path to dump file.
        db_dict: db_username
                 db_password
                 db_name

        """
        result = local("mysqldump --single-transaction \
                                  --user='%s' --password='%s' %s > %s" % (
                                         db_dict.get('db_username'),
                                         db_dict.get('db_password'),
                                         db_dict.get('db_name'),
                                         destination))
        if result.failed:
            abort("Export of database '%s' failed." % db_dict.get('db_name'))

