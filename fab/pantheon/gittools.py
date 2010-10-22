import os
import sys

sys.path.append('/opt/pantheon')
from tools.ptools import postback

from fabric.api import * 

import pantheon

def postback_gitstatus(project):
    """Send Atlas the git status with job_name='git_status' parameter. 
    project: project name. 
 
    """
    repo = GitRepo(project)
    status = repo.get_update_status()
    postback.postback({'status':status,'job_name':'git_status'})

def post_receive_hook(params):
    """Perform post-receive actions when changes are made to git repo.
    params: hook params from git stdin.

    If development environment HEAD is different from central repo HEAD,
    update the dev environment. This can occur if changes are pushed from
    a remote location to the central repo. If the HEADs are the same, then
    we assume that changes were pushed from dev to central repo and no update
    is needed.

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
                # Only update dev environment if HEAD commits don't match.
                if dev_head != repo_head:
                        local('curl http://127.0.0.1:8090/job/post_receive_update/' + \
                              'buildWithParameters?project=%s' % project)
        print "\n\n \
        The '%s' project is being updated in the development environment. \
               \n\n" % (project)
    else:
        print "\n\nWarning: No development environment for project '%s' was found." % (project)

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

    def get_update_status(self):
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

