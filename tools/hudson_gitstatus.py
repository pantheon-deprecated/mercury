import sys

sys.path.append('/opt/pantheon')
from fab.pantheon import gittools
 
if __name__ == '__main__':
    gittools.postback_gitstatus(sys.argv[1])

