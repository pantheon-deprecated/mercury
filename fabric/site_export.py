from fabric.api import *
from fabric.contrib.console import confirm

def export_site():
    '''Initialize the Pantheon system.'''
    local('whoami')
