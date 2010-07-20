from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from os.path import exists

env.hosts = ['localhost']

def ssh_loopback():
    with cd('~/.ssh'):
        local('rm -f id_rsa id_rsa.pub')
        local('ssh-keygen -trsa -b1024 -f id_rsa -N ""')
        local('cp id_rsa.pub authorized_keys')
        local('chmod 600 authorized_keys')
    run('echo Working')

def init():
    '''Initialize the Pantheon system.'''
    ssh_loopback()
