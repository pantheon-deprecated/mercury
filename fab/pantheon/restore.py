import os
import sys
import tempfile

import pantheon
from project import project

from fabric.api import local
from fabric.api import cd

class RestoreTools(project.BuildTools):

    def __init__(self, project, **kw):
        super(RestoreTools, self).__init__(project)
        self.destination = os.path.join(self.server.webroot, project)
        self.db_password = pantheon.random_string(10)
        self.working_dir = tempfile.mkdtemp()

    def extract(self, tarball):
        local('tar xzf %s -C %s' % (tarball, self.working_dir))

    def parse_backup(self):
        self.backup_project = os.listdir(self.working_dir)[0]

    def setup_database(self):
        for env in self.environments:
            db_dump = os.path.join(self.working_dir,
                                   self.backup_project,
                                   env,
                                   'database.sql')
            super(RestoreTools, self).setup_database(env,
                                                     self.db_password,
                                                     db_dump)
            local('rm -f %s' % db_dump)

    def restore_site_files(self):
        if os.path.exists(self.destination):
            local('rm -rf %s' % self.destination)
        local('mkdir -p %s' % self.destination)
        for env in self.environments:
            with cd(os.path.join(self.working_dir, self.backup_project)):
                local('rsync -avz %s %s' % (env, self.destination))

    def restore_repository(self):
        project_repo = os.path.join('/var/git/projects', self.project)
        backup_repo = os.path.join(self.working_dir,
                                   self.backup_project,
                                   '%s.git' % self.project)
        if os.path.exists(project_repo):
            local('rm -rf %s' % project_repo)
        local('rsync -avz %s/ %s/' % (backup_repo, project_repo))
        local('chmod -R g+w %s' % project_repo)

    def setup_vhost(self):
        super(RestoreTools, self).setup_vhost(self.db_password)

    def setup_permissions(self):
        super(RestoreTools, self).setup_permissions(handler='restore')

    def cleanup(self):
        local('rm -rf %s' % self.working_dir)

