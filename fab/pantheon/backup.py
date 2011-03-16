import os
import tempfile

from configobj import ConfigObj
from fabric.api import *

import pantheon

def remove(archive):
    """Remove a backup tarball from the server.
    archive: name of the archive to remove.

    """
    server = pantheon.PantheonServer()
    path = os.path.join(server.ftproot, archive)
    if os.path.exists(path):
        local('rm -f %s' % path)

class PantheonBackup():

    def __init__(self, name, project):
        """Initialize Backup Object.
        name: name of backup (resulting file: name.tar.gz)
        project: name of project to backup.

        """
        self.server = pantheon.PantheonServer()
        self.project =  project
        self.environments = pantheon.get_environments()
        self.working_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.working_dir, self.project)
        self.name = name + '.tar.gz'

    def get_dev_code(self, user, host):
        """USED FOR REMOTE DEV: Clone of dev git repo.

        """
        local('mkdir -p %s' % self.backup_dir)
        source = os.path.join(self.server.webroot, self.project, 'dev')
        destination = 'code'
        with cd(self.backup_dir):
            local('git clone %s -b %s %s' % (source,
                                             self.project,
                                             destination))
            # Manually set the origin URL so remote pushes have a destination.
            with cd(destination):
                local("sed -i 's/^.*url =.*$/\\turl = " + \
                "%s@%s.gotpantheon.com:\/var\/git\/projects\/%s/' .git/config"\
                % (user, host, self.project))

    def get_dev_files(self):
        """USED FOR REMOTE DEV: dev site files.

        """
        local('mkdir -p %s' % self.backup_dir)
        source = os.path.join(self.server.webroot, self.project,
                                      'dev/sites/default/files')
        destination = self.backup_dir
        # If 'dev_code' exists in backup_dir, this is a full dev-archive dump.
        # Place the files within the drupal site tree.
        if os.path.exists(os.path.join(self.backup_dir, 'dev_code/sites/default')):
            destination = os.path.join(self.backup_dir, 'dev_code/sites/default')
        local('rsync -avz %s %s' % (source, destination))

    def get_dev_data(self):
        """USED FOR REMOTE DEV: dev site data.

        """
        local('mkdir -p %s' % self.backup_dir)
        drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                                 self.project, 'dev'))
        destination = os.path.join(self.backup_dir, 'dev_database.sql')
        self._dump_data(destination, drupal_vars)

    def backup_files(self):
        """Backup all files for environments of a project.

        """
        local('mkdir -p %s' % self.backup_dir)
        for env in self.environments:
            source = os.path.join(self.server.webroot, self.project, env)
            local('rsync -avz %s %s' % (source, self.backup_dir))

    def backup_data(self):
        """Backup databases for environments of a project.

        """
        for env in self.environments:
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

    def finalize(self):
        """ Create archive, move to destination, remove working dir.

        """
        self.make_archive()
        self.move_archive()
        self.cleanup()

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

