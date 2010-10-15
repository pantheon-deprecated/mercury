import sys

from ptools import postback

def send_git_status(project):
    postback.postback_gitstatus(project)

if __name__ == '__main__':
    send_git_status(sys.argv[1])

