import os
import tempfile

import dbtools
import pantheon
import project
import jenkinstools
import postback

from fabric.api import *

class Updater(project.BuildTools):

    def __init__(self, project, environment):
        super(Updater, self).__init__(project)

        self.project_env = environment
        self.author = 'Jenkins User <jenkins@pantheon>'
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
            local('git fetch origin master')

        # Commit all changes in dev working-tree.
        self.code_commit('Core Update: Automated Commit.')

        with cd(os.path.join(self.project_path, 'dev')):
            with settings(warn_only=True):
                # Merge latest pressflow.
                merge = local('git pull origin master')
                print merge

            # Handle failed merges
            if merge.failed:
                print 'Merge failed.'
                if keep == 'ours':
                    print 'Re-merging - keeping local changes on conflict.'
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xours origin master')
                    print merge
                    local('git push')
                elif keep == 'theirs':
                    print 'Re-merging - keeping upstream changes on conflict.'
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xtheirs origin master')
                    print merge
                    local('git push')
                elif keep == 'force':
                    print 'Leaving merge conflicts. Please manually resolve.'
                else:
                    #TODO: How do we want to report this back to user?
                    print 'Rolling back failed changes.'
                    local('git reset --hard ORIG_HEAD')
                    return {'merge':'fail','log':merge}
            # Successful merge.
            else:
                local('git push')
        return {'merge':'success','log':merge}


    def code_update(self, tag, message):
        # Update code in 'dev' (Only used when updating from remote push)
        if self.project_env == 'dev':
            with cd(self.env_path):
                local('git pull')

        # Update code in 'test' (commit & tag in 'dev', fetch in 'test')
        elif self.project_env == 'test':
            self.code_commit(message)
            self._tag_code(tag, message)
            self._fetch_and_reset(tag)

        # Update code in 'live' (get latest tag from 'test', fetch in 'live')
        elif self.project_env == 'live':
            with cd(os.path.join(self.project_path, 'test')):
                tag = local('git describe --tags').rstrip('\n')
            self._fetch_and_reset(tag)
        local("apache2ctl -k graceful", capture=False)

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
        export = dbtools.export_data(self.project, source_env, tempdir)
        dbtools.import_data(self.project, self.project_env, export)
        local('rm -rf %s' % tempdir)

    def files_update(self, source_env):
        source = os.path.join(self.project_path,
                              '%s/sites/default/files' % source_env)
        dest = os.path.join(self.project_path,
                            '%s/sites/default/' % self.project_env)
        local('rsync -av --delete %s %s' % (source, dest))

    def drupal_updatedb(self):
        alias = '@%s_%s' % (self.project, self.project_env)
        with settings(warn_only=True):
            result = local('drush %s -by updb' % alias)
        json_out = pantheon.parse_drush_output(result)
        msgs = '\n'.join(['[%s] %s' % (o['type'], o['message'])
                        for o in json_out['log']])
        if (result.failed):
            jenkinstools.junit_fail(msgs, 'UpdateDB')
            postback.build_warning("Warning: UpdateDB encountered an error.")
            print("\n=== UpdateDB Debug Output ===\n%s\n" % msgs)
        else:
            jenkinstools.junit_pass(msgs, 'UpdateDB')

    def permissions_update(self):
        self.setup_permissions('update', self.project_env)

    def run_command(self, command):
        with cd(self.env_path):
            local(command, capture=False)

    def test_tag(self, tag):
        #test of existing tag
        with cd(self.env_path):
            with settings(warn_only=True):
                count = local('git tag | grep -c ' + tag)
                if count.strip() != "0":
                    abort('warning: tag ' + tag + ' already exists!')

    def _tag_code(self, tag, message):
        with cd(os.path.join(self.project_path, 'dev')):
            local('git checkout %s' % self.project)
            local('git tag "%s" -m "%s"' % (tag, message), capture=False)
            local('git push --tags')

    def _fetch_and_reset(self, tag):
        with cd(os.path.join(self.project_path, self.project_env)):
            local('git checkout %s' % self.project)
            local('git fetch -t')
            local('git reset --hard "%s"' % tag)

