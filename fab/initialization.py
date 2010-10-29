# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import tempfile

from fabric.api import *

import update
from pantheon import pantheon

def initialize(vps="none"):
    '''Initialize the Pantheon system.'''
    server = pantheon.PantheonServer()
    _initialize_support_account(server)
    _initialize_package_manager(server)
    _initialize_bcfg2(vps, server)
    _initialize_iptables(server)
    _initialize_drush()
    _initialize_solr(server)
    _initialize_hudson(server)
    _initialize_apache(server)

def init():
    '''Alias of "initialize"'''
    initialize()

def _initialize_support_account(server):
    '''Generate a public/private key pair for root.'''
    #local('mkdir -p ~/.ssh')
    #with cd('~/.ssh'):
    #    with settings(warn_only=True):
    #        local('[ -f id_rsa ] || ssh-keygen -trsa -b1024 -f id_rsa -N ""')

    '''Set up the Pantheon support account with sudo and the proper keys.'''
    sudoers = local('cat /etc/sudoers')
    if '%sudo ALL=(ALL) NOPASSWD: ALL' not in sudoers:
        local('echo "%sudo ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
    if 'pantheon' not in local('cat /etc/passwd'):
        if server.distro == 'ubuntu':
            local('useradd pantheon --base-dir=/var --comment="Pantheon Support"'
                  ' --create-home --groups=' + server.web_group + ',sudo --shell=/bin/bash')
        elif server.distro == 'centos':
            local('useradd pantheon --base-dir=/var --comment="Pantheon Support"'
                  ' --create-home  --shell=/bin/bash')
    with cd('~pantheon'):
        local('mkdir -p .ssh')
        local('chmod 700 .ssh')
        pantheon.copy_template('authorized_keys', '~pantheon/.ssh/')
        #local('cat ~/.ssh/id_rsa.pub > .ssh/authorized_keys')
        local('chmod 600 .ssh/authorized_keys')
        local('chown -R pantheon: .ssh')


def _initialize_package_manager(server):
    if server.distro == 'ubuntu':
        with cd(server.template_dir):
            local('cp apt.pantheon.list /etc/apt/sources.list.d/pantheon.list')
            local('cp apt.php.pin /etc/apt/preferences.d/php')
            local('cp apt.openssh.pin /etc/apt/preferences.d/openssh')
            local('apt-key add apt.ppakeys.txt')
        local('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')
    elif server.distro == 'centos':
        local('rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/5/x86_64/ius-release-1.0-6.ius.el5.noarch.rpm')
        local('rpm -Uvh http://yum.fourkitchens.com/pub/centos/5/noarch/fourkitchens-release-5-6.noarch.rpm')
        local('rpm --import http://hudson-ci.org/redhat/hudson-ci.org.key')
        local('wget http://hudson-ci.org/redhat/hudson.repo -O /etc/yum.repos.d/hudson.repo')
        local('yum -y install git17 --enablerepo=ius-testing')
        arch = local('uname -m').rstrip('\n')
        if (arch == "x86_64"):
            exclude_arch = "*.i?86"
        elif (arch == "i386" or arch == "i586" or arch == "i686"):
            exclude_arch = "*.x86_64"
        if exclude_arch:
            local('echo "exclude=%s" >> /etc/yum.conf' % exclude_arch)
    server.update_packages()


def _initialize_bcfg2(vps, server):
    if server.distro == 'ubuntu':
        local('apt-get install -y bcfg2-server gamin python-gamin python-genshi')
    elif server.distro == 'centos':
        local('yum -y install bcfg2 bcfg2-server gamin gamin-python python-genshi python-ssl python-lxml libxslt')
    pantheon.copy_template('bcfg2.conf', '/etc/')
    local('rm -f /etc/bcfg2.key bcfg2.crt')
    local('openssl req -batch -x509 -nodes -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -days 1000 -newkey rsa:2048 -keyout /tmp/bcfg2.key -noout')
    local('cp /tmp/bcfg2.key /etc/')
    local('openssl req -batch -new  -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -key /etc/bcfg2.key | openssl x509 -req -days 1000 -signkey /tmp/bcfg2.key -out /tmp/bcfg2.crt')
    local('cp /tmp/bcfg2.crt /etc/')
    local('chmod 0600 /etc/bcfg2.key')
    local('[ -h /var/lib/bcfg2 ] || rmdir /var/lib/bcfg2')
    local('ln -sf /opt/pantheon/bcfg2 /var/lib/')
    pantheon.copy_template('clients.xml', '/var/lib/bcfg2/Metadata')
    local('sed -i "s/^plugins = .*$/plugins = Bundler,Cfg,Metadata,Packages,Probes,Rules,TGenshi\\nfilemonitor = gamin/" /etc/bcfg2.conf')

    if server.distro == 'centos':
        '''temp bug fix for upstream tab issue in TGenshi'''
        local('sed -i "s/\t/    /" /usr/lib/python2.4/site-packages/Bcfg2/Server/Plugins/TGenshi.py')

    pantheon.restart_bcfg2()
    if (vps == "aws"):
        local('/usr/sbin/bcfg2 -vqed -p pantheon-aws', capture=False)
    elif (vps == "ebs"):
        local('/usr/sbin/bcfg2 -vqed -p pantheon-aws-ebs', capture=False)
    else:
        local('/usr/sbin/bcfg2 -vqed', capture=False)


def _initialize_iptables(server):
    local('/sbin/iptables-restore < /etc/pantheon/templates/iptables')
    if server.distro == 'centos':
        local('cp /etc/pantheon/templates/iptables /etc/sysconfig/iptables')
        local('chkconfig iptables on')
        local('service iptables start')
    else:
        local('cp /etc/pantheon/templates/iptables /etc/iptables.rules')


def _initialize_drush():
    local('[ ! -d drush ] || rm -rf drush')
    local('wget http://ftp.drupal.org/files/projects/drush-6.x-3.3.tar.gz')
    local('tar xvzf drush-6.x-3.3.tar.gz')
    local('rm -f drush-6.x-3.3.tar.gz')
    local('chmod 555 drush/drush')
    local('chown -R root: drush')
    local('rm -rf /opt/drush && mv drush /opt/')
    local('mkdir /opt/drush/aliases')
    local('ln -sf /opt/drush/drush /usr/local/bin/drush')
    local('drush dl drush_make')


def initialize_solr(server):
    temp_dir = tempfile.mkdtemp()
    with cd(temp_dir):
        local('wget http://apache.osuosl.org/lucene/solr/1.4.1/apache-solr-1.4.1.tgz')
        local('tar xvzf apache-solr-1.4.1.tgz')
        local('mkdir -p /var/solr')
        local('mv apache-solr-1.4.1/dist/apache-solr-1.4.1.war /var/solr/solr.war')
        local('cp -R apache-solr-1.4.1/example/solr %s' % server.template_dir)
        local('drush dl apachesolr') 
        local('cp apachesolr/schema.xml %s' % os.path.join(
                         server.template_dir, 'solr/conf'))
        local('cp apachesolr/solrconfig.xml %s' %  os.path.join(
                              server.template_dir, 'solr/conf'))
        local('chown -R ' + server.tomcat_owner + ':root /var/solr/')
    local('rm -rf ' + temp_dir)


def _initialize_hudson(server):
    sudoers = local('cat /etc/sudoers')
    hudson_sudoer = ('hudson ALL = NOPASSWD: /usr/local/bin/drush, '
                     '/usr/bin/fab, /usr/sbin/bcfg2, /usr/bin/python')
    if 'hudson ALL = NOPASSWD:' not in sudoers:
        local('echo "%s" >> /etc/sudoers' % hudson_sudoer)
    if server.distro == 'centos':
        local('sed -i "s/Defaults    requiretty/#Defaults    requiretty/" /etc/sudoers')
    local('usermod -aG ssl-cert hudson')
    local('/etc/init.d/hudson restart')


def _initialize_apache(server):
    if server.distro == 'ubuntu':
        local('a2dissite default')
        local('rm -f /etc/apache2/sites-available/default*')
        local('rm -f /var/www/*')
