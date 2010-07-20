from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from os.path import exists

env.hosts = ['pantheon@localhost']

def add_support_account():
    local('echo "%sudo ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
    local('useradd pantheon --base-dir=/var --comment="Pantheon Support" --create-home --groups=www-data,sudo --shell=/bin/bash')
    with cd('~pantheon'):
        local('mkdir .ssh')
        local('chmod 700 .ssh')
        local('cp /opt/pantheon/init/authorized_keys .ssh/')
        local('cat ~/.ssh/id_rsa.pub > .ssh/authorized_keys')
        local('chmod 600 .ssh/authorized_keys')
        local('chown -R pantheon: .ssh')

def initialize():
    '''Initialize the Pantheon system.'''
    #add_support_account()
    run('whoami')
    sudo('whoami')
    set_up_apt()

def set_up_apt():
    sudo('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')
