from fabric.api import local, cd
import os

CHRONOS = "https://code.getpantheon.com/sites/self/code"

def sync_repo():
    os.environ["GIT_SSL_CERT"] = "/etc/pantheon/system.pem"
    project_directory = os.listdir("/var/git/projects/")[0]
    with cd("/var/git/projects/%s" % project_directory):
        local("git push --all %s" % CHRONOS, capture=False)
        local("git fetch %s" % CHRONOS, capture=False)
