import os
import sys
import tempfile

import pantheon
import project

from fabric.api import local
from fabric.api import cd

class RestoreTools(project.BuildTools):

    def __init__(self, project, **kw):
        """ Initialize Restore object. Inherits base methods from BuildTools.

        """
        super(RestoreTools, self).__init__(project)
        self.destination = os.path.join(self.server.webroot, project)
        self.db_password = pantheon.random_string(10)
        self.working_dir = tempfile.mkdtemp()

    def extract(self, tarball):
        """ Extract the tarball to the working_dir.

        """
        #TODO: Write a more universal extractor and put in BuildTools.
        local('tar xzf %s -C %s' % (tarball, self.working_dir))

    def parse_backup(self):
        """ Get project name from extracted backup.

        """
        self.backup_project = os.listdir(self.working_dir)[0]

    def setup_database(self):
        """ Restore databases from backup.

        """
        for env in self.environments:
            db_dump = os.path.join(self.working_dir,
                                   self.backup_project,
                                   env,
                                   'database.sql')
            # Create database and import from dumpfile.
            super(RestoreTools, self).setup_database(env,
                                                     self.db_password,
                                                     db_dump,
                                                     False)
            # Cleanup dump file before copying files over.
            local('rm -f %s' % db_dump)

    def restore_site_files(self):
        """ Restore code from backup.

        """
        if os.path.exists(self.destination):
            local('rm -rf %s' % self.destination)
        local('mkdir -p %s' % self.destination)
        for env in self.environments:
            with cd(os.path.join(self.working_dir, self.backup_project)):
                local('rsync -avz %s %s' % (env, self.destination))

    def restore_repository(self):
        """ Restore GIT repo from backup.

        """
        project_repo = os.path.join('/var/git/projects', self.project)
        backup_repo = os.path.join(self.working_dir,
                                   self.backup_project,
                                   '%s.git' % self.backup_project)
        if os.path.exists(project_repo):
            local('rm -rf %s' % project_repo)
        local('rsync -avz %s/ %s/' % (backup_repo, project_repo))
        local('chmod -R g+w %s' % project_repo)

    def setup_vhost(self):
        """ Create vhost file using db_password.

        """
        super(RestoreTools, self).setup_vhost(self.db_password)

    def setup_permissions(self):
        """ Set permissions on project, and repo using the 'restore' handler.

        """
        super(RestoreTools, self).setup_permissions(handler='restore')

    def cleanup(self):
        """ Remove working_dir.

        """
        local('rm -rf %s' % self.working_dir)

