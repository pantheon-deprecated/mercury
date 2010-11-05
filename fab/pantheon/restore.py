from project import project

class RestoreTools(project.BuildTools):

    def __init__(self, project, **kw):
        super(RestoreTools, self).__init__(project)

    def extract(self, tarball):
        local('tar xzf %s -C %s' % (tarball, self.working_dir))

    def parse_backup(self):
        self.backup_project = os.listdir(self.working_dir)[0]

    def restore_database(self):
        for env in self.environments:
            db_dump = os.path.join(self.working_dir,
                                   self.backup_project,
                                   env,
                                   'database.sql')
            database = '%s_%s' % (self.project, env)
            username = self.project

            pantheon.create_database(database)
            pantheon.import_db_dump(db_dump, database)
            pantheon.set_database_grants(database, username, self.db_password)

            local('rm -f %s' % db_dump)

    def restore_files(self):
        if os.path.exists(self.destination):
            local('rm -rf %s' % self.destination)
        local('mkdir -p' % self.destination)
        for env in self.environments:
            with cd(os.path.join(self.working_dir, self.backup_project)):
                local('rsync -avz %s %s' % (env, self.destination))

