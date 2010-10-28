import install
import pantheon

class RestoreTools(install.InstallTools):

    def __init__(self, project, url):
        install.InstallTools.__init__(self, project)
        self.environments = pantheon.get_environments()

    def extract_backup(self, tarball):
        local('tar xzf %s -C %s' % (tarball, self.working_dir))

    def parse_backup(self):
        self.project = os.listdir(self.working_dir)[0]

    def restore_database(self):
        for env in self.environments:
            db_dump = os.path.join(self.working_dir, env, 'database.sql')
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
            with cd(os.path.join(self.working_dir, self.project)):
                local('rsync -avz %s %s' % (env, self.destination)

    def restore_repo(self):
        
