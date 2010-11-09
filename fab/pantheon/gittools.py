import os
import sys

from fabric.api import *

import pantheon

def post_receive_hook(params):
    """Perform post-receive actions when changes are made to git repo.
    params: hook params from git stdin.

    If development environment HEAD is different from central repo HEAD,
    update the dev environment. This can occur if changes are pushed from
    a remote location to the central repo. In this case, we call a Hudson job
    to update the development environment, then post back to Atlas with the
    status of the project.

    If the HEADs are the same, then we assume that changes were pushed from dev
    to central repo and no update to dev environment is needed. However, we may
    still need to update Atlas with the project status. If the author is Hudson
    we assume the originating Hudson job will post back to Atlas. Otherwise,
    call the post_receive_update job, but don't update the dev environment.

    NOTE: we use 'env -i' to clear environmental variables git has set when
    running hook operations.

    """
    (project, old_rev, new_rev) = _parse_hook_params(params)
    webroot = pantheon.PantheonServer().webroot
    dest = os.path.join(webroot, project, 'dev')

    if os.path.exists(dest):
        with cd(dest):
            # Hide output from showing on git's report back to user.
            with hide('running'):
                # Update metadata in dev environment.
                local('env -i git fetch')
                # Get last commit id for dev, and central repo.
                dev_head = local('env -i git rev-parse refs/heads/%s' % \
                        project).rstrip('\n')
                repo_head = local('env -i git rev-parse refs/remotes/origin/%s' % \
                        project).rstrip('\n')

                # Dev and central repo HEADs don't match.
                if dev_head != repo_head:
                    with settings(warn_only=True):
                        with hide('warnings'):
                            dev_update = local('env -i git pull', capture=False)
                    # Trigger Hudson job to update dev environment and set permissions.
                    local('curl http://127.0.0.1:8090/job/post_receive_update/' + \
                          'buildWithParameters?project=%s\\&dev_update=True' % project)
                    # Output status to the PUSH initiator.
                    if dev_update.failed:
                        print "\nWARNING: Development environment could not be updated."
                        print "\nPlease review any error messages above, and resolve any conflicts."
                        print "\n\n"
                    else:
                        print "\nDevelopment environment updated.\n"
                # Dev and Central repo HEADs match. 
                else:
                    author_name, author_email = local(
                            'env -i git log -1 --pretty=format:%an%n%ae ' +
                            '%s' % dev_head).rstrip('\n').split('\n')
                    # Code change initiated by user (not hudson job). Report back with status.
                    # However, don't update dev environment or permissions (dev_update=False param)
                    if ((author_name != 'Hudson User') and
                            (author_email != 'hudson@getpantheon')):
                        local('curl http://127.0.0.1:8090/job/post_receive_update/' + \
                              'buildWithParameters?project=%s\\&dev_update=False' % project)
    else:
        print "\n\n"
        print "WARNING: No development environment for '%s', was found.\n" % (project)

def _parse_hook_params(params):
    """Parse the params received during a git push.
    Return project name, old revision, new revision.

    """
    (revision_old, revision_new, refs) = params.split(' ')
    project = refs.split('/')[2].rstrip('\n')
    return (project, revision_old, revision_new)


class GitRepo():

    def __init__(self, project):
        self.project = project
        self.repo = os.path.join('/var/git/projects', self.project)
        self.server = pantheon.PantheonServer()
        self.project_path = os.path.join(self.server.webroot, self.project)

    def get_repo_status(self):
        """Return dict of dev/test and test/live diffs, and last 10 log entries.

        """

        head = self._get_last_commit('dev')
        test = self._get_last_commit('test')
        live = self._get_last_commit('live')

        #dev/test diff
        diff_dev_test = self._get_diff_stat(test, head)
        #test/live diff
        diff_test_live = self._get_diff_stat(live, test)
        #log
        log = self._get_log(10)

        return {'diff_dev_test':diff_dev_test,
                'diff_test_live':diff_test_live,
                'log':log}

    def _get_last_commit(self, env):
        """Get last commit or tag for the given environment.
        env: environment.

        returns commit hash for dev, or current tag for test/live.

        """
        with cd(os.path.join(self.project_path, env)):
            if env == 'dev':
                ref = local('git rev-parse refs/heads/%s' %  self.project)
            else:
                ref = local('git describe --tags %s' % self.project).rstrip('\n')
        return ref

    def _get_diff_stat(self, base, other):
        """return diff --stat of base/other.
        base: commit hash or tag
        other: commit hash or tag

        """
        with cd(self.repo):
            diff = local('git diff --stat %s %s' % (base, other))
        return diff

    def _get_log(self, num_entries):
        """Return num_entries of git log.
        num_entries: int. Number of entries to return

        """
        with cd(self.repo):
            log = local('git log -n%s %s' % (num_entries, self.project))
        return log

