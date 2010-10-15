import os

from fabric.api import cd
from fabric.api import local

def _get_webroot():
    if os.path.exists('/etc/debian_version'):
        return '/var/www/'
    elif os.path.exists('/etc/redhat-release'):
        return '/var/www/html/'

class GitRepo():
    
    def __init__(self, project):
        self.project = project
        self.repo = os.path.join('/var/git/projects', self.project)
        self.project_path = os.path.join(_get_webroot(), self.project)

    def get_update_status(self, head=None):
        """Return dict of dev/test and test/live diffs, and last 10 log entries.
        head: Optional. Last dev commit hash. If being called from post-receive
                        hook, commit is known and can be passed as parm.

        """
        if not head:
            head = self._get_last_commit('dev')
        test = self._get_last_commit('test')
        live = self._get_last_commit('live')
        
        #dev/test diff
        diff_dev_test = self._get_diff(test, head)
        #test/live diff
        diff_test_live = self._get_diff(live, test)
        #log
        log = self._get_log(10)

        return {'job_name':'git_status',
                'diff_dev_test':diff_dev_test,
                'diff_test_live':diff_test_live,
                'log':log}

    def _get_last_commit(self, env):
        """Get last commit or tag for the given environment.
        env: environment.
        
        returns commit hash for dev, or current tag for test/live.

        """
        if env == 'dev':
            with cd(self.repo):
                 ref = local('git log -n1 --pretty=format:%H ' +
                             '%s' %  self.project)
        else:
            with cd(os.path.join(self.project_path, env)):
                ref = local('env -i git describe --tags %s' % self.project).rstrip('\n')
        return ref

    def _get_diff(self, base, other):
        """return diff --stat of base/other.
        base: commit hash or tag
        other: commit hash or tag

        """
        with cd(self.repo):
            local('env -i git checkout %s' % self.project)
            diff = local('env -i git diff --stat %s %s' % (base, other))
        return diff

    def _get_log(self, num_entries):
        """Return num_entries of git log.
        num_entries: int. Number of entries to return

        """
        with cd(self.repo):
            log = local('env -i git log -n%s %s' % (num_entries, self.project))
        return log

