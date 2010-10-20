import os
import tempfile

import pantheon

from fabric.api import *

class Updater():

    def __init__(self, project, environment=''):
        self.project = project
        self.environment = environment
        self.author = 'Hudson User <hudson@pantheon>'
        self.server = pantheon.PantheonServer()
        self.project_path = os.path.join(self.server.webroot, self.project)
        self.env_path = os.path.join(self.project_path, environment)


    def core_update(self, keep=None):
        """Update core in dev environment.

        keep: Option when merge fails:
              'ours': Keep local changes when there are conflicts.
              'theirs': Keep upstream changes when there are conflicts.
              'force': Leave failed merge in working-tree (manual resolve).
              None: Reset to ORIG_HEAD if merge fails.
                             
        """
        # Update pantheon core master branch
        with cd('/var/git/projects/%s' % self.project):
            local('git pull git://gitorious.org/pantheon/6.git master')

        # Commit all changes in dev working-tree.
        self.code_commit('Core Update: Automated Commit.')

        with cd(os.path.join(self.project_path, 'dev')):
            with settings(warn_only=True):
                # Merge latest pressflow.
                merge = local('git pull origin master', capture=False)

            # Handle failed merges
            if merge.failed:
                print 'Merge failed.'
                if keep == 'ours':
                    print 'Re-merging - keeping local changes on conflict.'
                    local('git reset --hard ORIG_HEAD')
                    local('git pull -s recursive -Xours origin master')
                    local('git push')
                elif keep == 'theirs':
                    print 'Re-merging - keeping upstream changes on conflict.'
                    local('git reset --hard ORIG_HEAD')
                    local('git pull -s recursive -Xtheirs origin master')
                    local('git push')
                elif keep == 'force':
                    print 'Leaving merge conflicts. Please manually resolve.'
                else:
                    #TODO: How do we want to report this back to user?
                    print 'Rolling back failed changes.'
                    local('git reset --hard ORIG_HEAD')
            # Successful merge.
            else:
                local('git push')
                

    def code_update(self, tag, message):
        # Update code in 'dev' (Only used when updating from remote push)
        if self.environment == 'dev':
            self.code_commit('Automated Commit. Updating from remote push.')
            with cd(self.env_path):
                local('git pull')

        # Update code in 'test' (commit & tag in 'dev', fetch in 'test')
        elif self.environment == 'test':
            self.code_commit('Automated Commit.')
            self._tag_code(tag, message)
            self._fetch_and_reset(tag)

        # Update code in 'live' (get latest tag from 'test', fetch in 'live')
        elif self.environment == 'live':
            with cd(os.path.join(self.project_path, 'test')):
                tag = local('git describe --tags').rstrip('\n')
            self._fetch_and_reset(tag)
    
    def code_commit(self, message):
        with cd(os.path.join(self.project_path, 'dev')):
            local('git checkout %s' % self.project)
            local('git add -A .')
            with settings(warn_only=True):
                local('git commit --author="%s" -m "%s"' % (
                       self.author, message), capture=False)
            local('git push')

    def data_update(self, source_env):
        tempdir = tempfile.mkdtemp()
        export = pantheon.export_data(self.project, source_env, tempdir)
        pantheon.import_data(self.project, self.environment, export)
        local('rm -rf %s' % tempdir)

    def files_update(self, source_env):
        source = os.path.join(self.project_path,
                              '%s/sites/default/files' % source_env)
        dest = os.path.join(self.project_path,
                            '%s/sites/default/' % self.environment)
        local('rsync -av --delete %s %s' % (source, dest))

    def permissions_update(self):
        owner = server.get_ldap_group()
        with cd(self.server.webroot):
            # Force ownership on everything exept files directory.
            local("find %s \( -path %s/%s/sites/default/files -prune \) \
                   -o \( -exec chown %s:%s '{}' \; \)" % (self.project,
                                                          self.project,
                                                          self.environment,
                                                          owner, owner))
        site_path = os.path.join(self.project_path,
                                 '%s/sites/default' % self.environment)
        with cd(site_path):
            if pantheon.is_drupal_installed(self.project, self.environment):
                local('chmod 440 settings.php')
                local('chown %s:%s settings.php' % (owner,
                                                    self.server.web_group))
            else:
                # If drupal is not installed, settings.php needs to be owned by
                # apache, and have write permissions.
                local('chmod 660 settings.php')
                local('chown %s:%s settings.php' % (self.server.web_group,
                                                    self.server.web_group))
                
            local('chmod 440 pantheon.settings.php')
            local('chown %s:%s pantheon.settings.php' % (owner,
                                                         self.server.web_group))

    def run_command(self, command):
        with cd(self.env_path):
            local(command, capture=False)

    def test_tag(self, tag):
        #test of existing tag
        with cd(self.env_path):
            with settings(warn_only=True):
                count = local('git tag | grep -c ' + tag)
                if count == "0":
                    abort('warning: tag ' + tag + ' already exists!')

    def _tag_code(self, tag, message):
        with cd(os.path.join(self.project_path, 'dev')):
            local('git checkout %s' % self.project)
            local('git tag "%s" -m "%s"' % (tag, message), capture=False)
            local('git push --tags')

    def _fetch_and_reset(self, tag):
        with cd(os.path.join(self.project_path, self.environment)):
            local('git checkout %s' % self.project)
            local('git fetch -t')
            local('git reset --hard "%s"' % tag)

