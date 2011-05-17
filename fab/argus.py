from fabric.api import *
from pantheon import ygg
import sys

configuration = ygg.get_config()
STORAGE = '/var/lib/jenkins/jobs/argus/workspace'
WEBKIT2PNG = '/opt/pantheon/fab/webkit2png.py'
LOG = '{0}/webkit2png.log'.format(STORAGE)

def main(project,env):
    if not project:
        for p in configuration:
            with settings(warn_only=True):
                local('mkdir -p {0}/{1}'.format(STORAGE, p))
            for e in configuration[p]['environments']:
                _screenshot(p,e)
    elif project and not env:
        with settings(warn_only=True):
            local('mkdir -p {0}/{1}'.format(STORAGE, project))
        for e in configuration[project]['environments']:
            _screenshot(project,e)
    elif project and env:
        with settings(warn_only=True):
            local('mkdir -p {0}/{1}'.format(STORAGE, project))
        _screenshot(project,env)

def _screenshot(p, e):
        alias = configuration[p]['environments'][e]['apache']['ServerAlias']
        url = 'http://{0}'.format(alias)
        fname = '{0}_{1}.png'.format(p, e)
        fpath = '{0}/{1}/{2}'.format(STORAGE, p, fname)
        local('xvfb-run --server-args="-screen 0, 640x480x24" python {0} --log="{1}" {2} > {3}'.format(WEBKIT2PNG, LOG, url, fpath))

if __name__ == '__main__':
    project = sys.argv[1] if len(sys.argv) >= 2 else None
    env = sys.argv[2] if len(sys.argv) == 3 else None
    main(project, env)
