import httplib
import json
import os
import tempfile

import dbtools
import pantheon
import project
import postback
import logger
import drupaltools

from fabric.api import *

class Updater(project.BuildTools):

    def __init__(self, environment=None):
        super(Updater, self).__init__()

        self.log = logger.logging.getLogger('pantheon.update.Updater')
        context = {"project":self.project}
        if environment:
            assert environment in self.environments, \
                   'Environment not found in project: {0}'.format(self.project)
            context['environment'] = environment
            self.update_env = environment
            self.author = 'Jenkins User <jenkins@pantheon>'
            self.env_path = os.path.join(self.project_path, environment)
        self.log = logger.logging.LoggerAdapter(self.log, context)

    def core_update(self, keep=None):
        """Update core in dev environment.

        keep: Option when merge fails:
              'ours': Keep local changes when there are conflicts.
              'theirs': Keep upstream changes when there are conflicts.
              'force': Leave failed merge in working-tree (manual resolve).
              None: Reset to ORIG_HEAD if merge fails.

        """
        self.log.info('Initialized core update.')
        # Update pantheon core master branch
        with cd('/var/git/projects/%s' % self.project):
            local('git fetch origin master')

        # Commit all changes in dev working-tree.
        self.code_commit('Core Update: Automated Commit.')

        with cd(os.path.join(self.project_path, 'dev')):
            with settings(warn_only=True):
                # Merge latest pressflow.
                merge = local('git pull origin master')
                self.log.info(merge)

            # Handle failed merges
            if merge.failed:
                self.log.error('Merge failed.')
                if keep == 'ours':
                    self.log.info('Re-merging - keeping local changes on ' \
                                  'conflict.')
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xours origin master')
                    self.log.info(merge)
                    local('git push')
                elif keep == 'theirs':
                    self.log.info('Re-merging - keeping upstream changes on ' \
                                  'conflict.')
                    local('git reset --hard ORIG_HEAD')
                    merge = local('git pull -s recursive -Xtheirs origin ' \
                                  'master')
                    self.log.info(merge)
                    local('git push')
                elif keep == 'force':
                    self.log.info('Leaving merge conflicts. Please manually ' \
                                  'resolve.')
                else:
                    #TODO: How do we want to report this back to user?
                    self.log.info('Rolling back failed changes.')
                    local('git reset --hard ORIG_HEAD')
                    return {'merge':'fail','log':merge}
            # Successful merge.
            else:
                local('git push')
                self.log.info('Merge successful.')
        self.log.info('Core update successful.')
        return {'merge':'success','log':merge}


    def code_update(self, tag, message):
        self.log.info('Initialized code update.')
        try:
            # Update code in 'dev' (Only used when updating from remote push)
            if self.update_env == 'dev':
                with cd(self.env_path):
                    local('git pull')

            # Update code in 'test' (commit & tag in 'dev', fetch in 'test')
            elif self.update_env == 'test':
                self.code_commit(message)
                self._tag_code(tag, message)
                self._fetch_and_reset(tag)

            # Update code in 'live' (get latest tag from 'test', fetch in
            # 'live')
            elif self.update_env == 'live':
                with cd(os.path.join(self.project_path, 'test')):
                    tag = local('git describe --tags --abbrev=0').rstrip('\n')
                self._fetch_and_reset(tag)
        except:
            self.log.exception('Code update encountered a fatal error.')
            raise
        else:
            self.log.info('Code update successful.')
        self.log.info('Gracefully restarting apache.')
        local("apache2ctl -k graceful", capture=False)

    def code_commit(self, message):
        try:
            with cd(os.path.join(self.project_path, 'dev')):
                local('git checkout %s' % self.project)
                local('git add -A .')
                with settings(warn_only=True):
                    local('git commit --author="%s" -m "%s"' % (
                          self.author, message), capture=False)
                local('git push')
        except:
            self.log.exception('Code commit encountered a fatal error.')
            raise
        else:
            self.log.info('Code commit successful.')

    def data_update(self, source_env):
        self.log.info('Initialized data sync')
        try:
            tempdir = tempfile.mkdtemp()
            export = dbtools.export_data(self, source_env, tempdir)
            dbtools.import_data(self, self.update_env, export)
            local('rm -rf %s' % tempdir)
        except:
            self.log.exception('Data sync encountered a fatal error.')
            raise
        else:
            self.log.info('Data sync successful.')

    def files_update(self, source_env):
        self.log.info('Initialized file sync')
        try:
            self.log.info('Attempting sync via Pantheon files API...')
            count = _file_api_clone(source_env, self.update_env)
            if count > 0:
                self.log.info('Sync via files API succeeded.')
            else:
                self.log.info('Attempting Rsync...')
                source = os.path.join(self.project_path,
                                      '%s/sites/default/files' % source_env)
                dest = os.path.join(self.project_path,
                                    '%s/sites/default/' % self.update_env)
                local('rsync -av --delete %s %s' % (source, dest))
        except:
            self.log.exception('File sync encountered a fatal error.')
            raise
        else:
            self.log.info('File sync successful.')

    def drupal_updatedb(self):
        self.log.info('Initiated Updatedb.')
        try:
            alias = '@%s_%s' % (self.project, self.update_env)
            result = drupaltools.updatedb(alias)
        except:
            self.log.exception('Updatedb encountered a fatal error.')
            raise
        else:
            self.log.info('Updatedb complete.')
            pantheon.log_drush_backend(result, self.log)

    def run_cron(self):
        self.log.info('Initialized cron.')
        try:
            with settings(warn_only=True):
                result = local("drush @%s_%s -b cron" %
                               (self.project, self.update_env))
        except:
            self.log.exception('Cron encountered a fatal error.')
            raise
        else:
            pantheon.log_drush_backend(result, self.log)

    def solr_reindex(self):
        self.log.info('Initialized solr-reindex.')
        try:
            with settings(warn_only=True):
                result = local("drush @%s_%s -b solr-reindex" %
                               (self.project, self.update_env))
        except:
            self.log.exception('Solr-reindex encountered a fatal error.')
            raise
        else:
            pantheon.log_drush_backend(result, self.log)

    def restart_varnish(self):
        self.log.info('Restarting varnish.')
        try:
            with settings(warn_only=True):
                local("/etc/init.d/varnish restart")
        except:
            self.log.exception('Encountered an error during restart.')
            raise

    def permissions_update(self):
        self.log.info('Initialized permissions update.')
        try:
            self.setup_permissions('update', self.update_env)
        except Exception as e:
            self.log.exception('Permissions update encountered a fatal error.')
            raise
        else:
            self.log.info('Permissions update successful.')

    def run_command(self, command):
        try:
            with cd(self.env_path):
                local(command, capture=False)
        except:
            self.log.exception('Encountered a fatal error while running %s' %
                               command)
            raise

    def test_tag(self, tag):
        try:
            #test of existing tag
            with cd(self.env_path):
                with settings(warn_only=True):
                    count = local('git tag | grep -c ' + tag)
                    if count.strip() != "0":
                        abort('warning: tag ' + tag + ' already exists!')
        except:
            self.log.exception('Encountered a fatal error while tagging code.')
            raise

    def _tag_code(self, tag, message):
        try:
            with cd(os.path.join(self.project_path, 'dev')):
                local('git checkout %s' % self.project)
                local('git tag "%s" -m "%s"' % (tag, message), capture=False)
                local('git push --tags')
        except:
            self.log.exception('Encountered a fatal error while tagging code.')
            raise

    def _fetch_and_reset(self, tag):
        try:
            with cd(os.path.join(self.project_path, self.update_env)):
                local('git checkout %s' % self.project)
                local('git fetch -t')
                local('git reset --hard "%s"' % tag)
        except:
            self.log.exception('Fetch and reset encountered a fatal error.')
            raise


def _file_api_clone(source, destination):
    """Make POST request to files server.
    Returns dict of response data.

    """
    host = 'files.getpantheon.com'
    port = 443
    certificate = '/etc/pantheon/system.pem'
    path = '/sites/self/environments/%s/files?clone-from-environment=%s' % (destination, source)
    connection = httplib.HTTPSConnection(host,
                                         port,
                                         key_file = certificate,
                                         cert_file = certificate)

    connection.request('POST', path)
    response = connection.getresponse()

    if response.status == 404:
        return None
    if response.status == 403:
        return False

    try:
        return json.loads(response.read())
    except:
        print('Response code: %s' % response.status)
        raise

