import sys

from ptools import postback
from ptools import gittools

def main(project):
    repo = gittools.GitRepo(project)
    status = repo.get_update_status()
    postback.postback({'status':status,'job_name':'git_status'})

if __name__ == '__main__':
    main(sys.argv[1])

