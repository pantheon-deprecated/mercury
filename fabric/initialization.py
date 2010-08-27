# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *

import pantheon
import update

def initialize(vps="none"):
    '''Initialize the Pantheon system.'''
    server = pantheon.PantheonServer()
    _initialize_support_account()
    _initialize_package_manager(server)
    _initialize_bcfg2(vps)
    _initialize_drush()
    _initialize_pantheon(server)
    _initialize_solr(server)
    _initialize_hudson()
    _initialize_iptables(server)
    _initialize_pressflow()

def init():
    '''Alias of "initialize"'''
    initialize()

def _initialize_support_account():
    '''Generate a public/private key pair for root.'''
    local('mkdir -p ~/.ssh')
    with cd('~/.ssh'):
        with settings(warn_only=True):
            local('[ -f id_rsa ] || ssh-keygen -trsa -b1024 -f id_rsa -N ""')

    '''Set up the Pantheon support account with sudo and the proper keys.'''
    sudoers = local('cat /etc/sudoers')
    if '%sudo ALL=(ALL) NOPASSWD: ALL' not in sudoers:
        local('echo "%sudo ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
    if 'pantheon' not in local('cat /etc/passwd'):
        if server.distro == 'ubuntu':
            local('useradd pantheon --base-dir=/var --comment="Pantheon Support"'
                  ' --create-home --groups=www-data,sudo --shell=/bin/bash')
         elif self.distro == 'centos':
             local('useradd pantheon --base-dir=/var --comment="Pantheon Support"'
                  ' --create-home --shell=/bin/bash')
    with cd('~pantheon'):
        local('mkdir -p .ssh')
        local('chmod 700 .ssh')
        local('cp /opt/pantheon/fabric/authorized_keys .ssh/')
        local('cat ~/.ssh/id_rsa.pub > .ssh/authorized_keys')
        local('chmod 600 .ssh/authorized_keys')
        local('chown -R pantheon: .ssh')

def _initialize_package_manager(server):
    if server.distro == 'ubuntu':
        with cd('/opt/pantheon/fabric'):
            local('cp pantheon.list /etc/apt/sources.list.d/')
            local('cp lucid /etc/apt/preferences.d/')
            local('apt-key add gpgkeys.txt')
        local('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')
    elif self.distro == 'centos':
        local('rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/5/x86_64/ius-release-1-4.ius.el5.noarch.rpm')
        local('rpm -Uvh http://yum.fourkitchens.com/pub/centos/5/noarch/fourkitchens-release-5-6.noarch.rpm')
        local('rpm --import http://hudson-ci.org/redhat/hudson-ci.org.key')
        local('wget http://hudson-ci.org/redhat/hudson.repo -O /etc/yum.repos.d/hudson.repo')
    server.update_packages()
        
def _initialize_bcfg2(vps):
    if server.distro == 'ubuntu':
        local('apt-get install -y bcfg2-server gamin python-gamin python-genshi')
    elif self.distro == 'centos':
        local('yum -y install bcfg2 bcfg2-server gamin gamin-python python-genshi python-ssl python-lxml libxslt')
    with cd('/opt/pantheon/fabric'):
        local('cp bcfg2.conf /etc/')
    local('rm -f /etc/bcfg2.key bcfg2.crt')
    local('openssl req -batch -x509 -nodes -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -days 1000 -newkey rsa:2048 -keyout /tmp/bcfg2.key -noout')
    local('cp /tmp/bcfg2.key /etc/')
    local('openssl req -batch -new  -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -key /etc/bcfg2.key | openssl x509 -req -days 1000 -signkey /tmp/bcfg2.key -out /tmp/bcfg2.crt')
    local('cp /tmp/bcfg2.crt /etc/')
    local('chmod 0600 /etc/bcfg2.key')
    local('[ -h /var/lib/bcfg2 ] || rmdir /var/lib/bcfg2')
    local('ln -sf /opt/pantheon/bcfg2 /var/lib/')
    local('cp /opt/pantheon/fabric/clients.xml /var/lib/bcfg2/Metadata/')
    local('sed -i "s/^plugins = .*$/plugins = Bundler,Cfg,Metadata,Packages,Probes,Rules,TGenshi\\nfilemonitor = gamin/" /etc/bcfg2.conf')
    pantheon.restart_bcfg2()
    if (vps == "aws"):
        sudo('/usr/sbin/bcfg2 -vqed -p pantheon-aws')
    elif (vps == "ebs"):
        sudo('/usr/sbin/bcfg2 -vqed -p pantheon-aws-ebs')
    else:
        sudo('/usr/sbin/bcfg2 -vqed')

def _initialize_drush():
    local('[ ! -d drush ] || rm -rf drush')
    local('wget http://ftp.drupal.org/files/projects/drush-6.x-3.3.tar.gz')
    local('tar xvzf drush-6.x-3.3.tar.gz')
    local('chmod 555 drush/drush')
    local('chown -R root: drush')
    local('rm -rf /opt/drush && mv drush /opt/')
    local('ln -sf /opt/drush/drush /usr/local/bin/drush')
    local('drush dl drush_make')

def _initialize_pantheon(server):
    local('rm -rf %s' % server.webroot())
    local('drush make /etc/pantheon/pantheon.make ' + server.webroot() + 'pantheon_dev/')

def _initialize_solr(server):
    local('[ ! -d apache-solr-1.4.1 ] || rm -rf apache-solr-1.4.1')
    local('wget http://apache.osuosl.org/lucene/solr/1.4.1/apache-solr-1.4.1.tgz')
    local('tar xvzf apache-solr-1.4.1.tgz')
    local('mkdir -p /var/solr')
    local('mv apache-solr-1.4.1/dist/apache-solr-1.4.1.war /var/solr/solr.war')
    local('cp -R apache-solr-1.4.1/example/solr /opt/pantheon/fabric/templates/')
    local('cp ' + server.webroot() + 'pantheon_dev/sites/all/modules/apachesolr/schema.xml /opt/pantheon/fabric/templates/solr/conf/')
    local('cp ' + server.webroot() + 'pantheon_dev/sites/all/modules/apachesolr/solrconfig.xml /opt/pantheon/fabric/templates/solr/conf/')
    local('rm -rf apache-solr-1.4.1')
    local('rm apache-solr-1.4.1.tgz')
    local('cp -R /opt/pantheon/fabric/templates/solr /var/solr/pantheon_dev')
    local('cp -a /var/solr/pantheon_dev /var/solr/pantheon_test')
    local('cp -a /var/solr/pantheon_dev /var/solr/pantheon_live')
    local('chown -R tomcat6:root /var/solr/')

def _initialize_hudson():
    sudoers = local('cat /etc/sudoers')
    hudson_sudoer = ('hudson ALL = NOPASSWD: /usr/local/bin/drush,'
                     ' /etc/pantheon/init.sh, /usr/bin/fab, /usr/sbin/bcfg2')
    if 'hudson ALL = NOPASSWD:' not in sudoers:
        local('echo "%s" >> /etc/sudoers' % hudson_sudoer)
    local('usermod -a -G shadow hudson')
    local('/etc/init.d/hudson restart')

def _initialize_iptables(server):
    server.setup_iptables()

def _initialize_pressflow():
    local('mkdir -p ' + server.webroot() + 'pantheon_dev/sites/default/files')
    local('mkdir -p ' +server.webroot()  + 'pantheon_dev/sites/all/files')
    local('echo "files/*" > ' + server.webroot() + 'pantheon_dev/sites/.gitignore')
    local('echo "!.gitignore" >> ' + server.webroot() + 'pantheon_dev/sites/.gitignore')
    local('touch pantheon_dev/sites/all/files/.gitignore')
    local('touch ' + server.webroot() + 'pantheon_dev/sites/default/files/.gitignore')
    local('cp ' + server.webroot() + 'pantheon_dev/sites/default/default.settings.php ' + server.webroot() + 'pantheon_dev/sites/default/settings.php')
    local('cat /opt/pantheon/fabric/templates/newsite.settings.php >> ' + server.webroot() + 'pantheon_dev/sites/default/settings.php')
    local('mkdir ' + server.webroot() + 'pantheon_live')
    with cd(server.webroot() + 'pantheon_dev'):
        local('git init')
        local('git add .')
        local('git commit -m "initial branch commit"')
        local('git checkout -b pantheon_dev')
    local('git clone ' + server.webroot() + 'pantheon_dev ' + server.webroot() + 'pantheon_test')
    with cd(server.webroot() + 'pantheon_test'):
        local('git checkout master')
        local('git update-index --assume-unchanged profiles/default/default.profile sites/default/settings.php')
        local('git archive master | sudo tar -x -C ' + server.webroot() + 'pantheon_live')
    local('sed -i "s/pantheon_dev/pantheon_test/g" ' + server.webroot() + 'pantheon_test/sites/default/settings.php ' + server.webroot() + 'pantheon_test/profiles/default/default.profile')
    local('sed -i "s/pantheon_dev/pantheon_live/g" ' + server.webroot() + 'pantheon_live/sites/default/settings.php ' + server.webroot() + 'pantheon_live/profiles/default/default.profile')
    update.update_permissions(server.webroot() + 'pantheon_dev')
    update.update_permissions(server.webroot() + 'pantheon_test')
    update.update_permissions(server.webroot() + 'pantheon_live')
