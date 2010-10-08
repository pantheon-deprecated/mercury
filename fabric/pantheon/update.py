import os
import tempfile

import pantheon

from fabric.api import *

class Updater():

    def __init__(self, project, environment):
        self.project = project
        self.environment = environment
        self.author = 'Hudson User <hudson@pantheon>'
        self.server = pantheon.PantheonServer()
        self.project_path = os.path.join(self.server.webroot, self.project)
        self.env_path = os.path.join(self.project_path, environment)

    def code_update(self, tag, message):

        # Update code in 'test' (commit & tag in 'dev', fetch in 'test')
        if self.environment == 'test':
            self.code_commit('Automated Commit.')
            self._tag_code(tag, message)
            self._fetch_and_reset(tag)

        # Update code in 'live' (get latest tag from 'test', fetch in 'live')
        elif self.environment == 'live':
            with cd(os.path.join(self.project_path, 'test')):
                tag = local('git describe').rstrip('\n')
            self._fetch_and_reset(tag)
    
    def code_commit(self, message):
        with cd(os.path.join(self.project_path, 'dev')):
            local('git checkout %s' % self.project)
            local('git add -A .')
            with settings(warn_only=True):
                local('git commit --author="%s" -m "%s"' % (self.author, message))
            local('git push')

    def data_update(self, source_env):
        tempdir = tempfile.mkdtemp()
        export = pantheon.export_data(self.project, source_env, tempdir)
        pantheon.import_data(self.project, self.environment, export)
        local('rm -rf %s' % tempdir)

    def files_update(self, source_env):
        source = os.path.join(self.project_path, '%s/sites/default/files' % source_env)
        dest = os.path.join(self.project_path,'%s/sites/default/' % self.environment)
        local('rsync -av --delete %s %s' % (source, dest))

    def permissions_update(self):
        with cd(self.server.webroot):
            local('chown -R root:%s %s' % (self.server.web_group, self.project))
        site_path = os.path.join(self.project_path, '%s/sites/default' % self.environment)
        with cd(site_path):
            local('chmod 440 settings.php')
            local('chmod 440 pantheon.settings.php')

    def run_command(self, command):
        with cd(self.env_path):
            local(command, capture=False)

    def _tag_code(self, tag, message):
        with cd(os.path.join(self.project_path, 'dev')):
            local('git checkout %s' % self.project)
            local('git tag "%s" -m "%s"' % (tag, message),  capture=False)
            local('git push --tags')

    def _fetch_and_reset(self, tag):
        with cd(os.path.join(self.project_path, self.environment)):
            local('git checkout %s' % self.project)
            local('git fetch -t')
            local('git reset --hard "%s"' % tag)

