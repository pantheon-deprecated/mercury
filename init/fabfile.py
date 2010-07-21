from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from os.path import exists
from time import sleep

env.hosts = ['pantheon@localhost']

def initialize_support_account():
    '''Generate a public/private key pair for root.'''
    local('mkdir ~/.ssh')
    with cd('~/.ssh'):
        with settings(warn_only=True):
            local('ssh-keygen -trsa -b1024 -f id_rsa -N ""')

    '''Set up the Pantheon support account with sudo and the proper keys.'''
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
    initialize_support_account()
    initialize_aptitude()
    initialize_bcfg2()
    initialize_drush()
    initialize_pantheon()
    initialize_solr()
    initialize_hudson()
    initialize_pressflow()

def initialize_aptitude():
    with cd('/opt/pantheon/init'):
        sudo('cp pantheon.list /etc/apt/sources.list.d/')
        sudo('cp lucid /etc/apt/preferences.d/')
        sudo('apt-key add gpgkeys.txt')
    sudo('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')
    sudo('apt-get update')
    sudo('apt-get -y dist-upgrade')

def initialize_bcfg2():
    sudo('apt-get install -y bcfg2-server gamin python-gamin python-genshi')

    with cd('/opt/pantheon/init'):
        sudo('cp bcfg2.conf /etc/')
    run('openssl req -batch -x509 -nodes -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -days 1000 -newkey rsa:2048 -keyout /tmp/bcfg2.key -noout')
    sudo('cp /tmp/bcfg2.key /etc/')
    run('openssl req -batch -new  -subj "/C=US/ST=California/L=San Francisco/CN=localhost" -key /etc/bcfg2.key | openssl x509 -req -days 1000 -signkey /tmp/bcfg2.key -out /tmp/bcfg2.crt')
    sudo('cp /tmp/bcfg2.crt /etc/')
    sudo('chmod 0600 /etc/bcfg2.key')
    sudo('rmdir /var/lib/bcfg2')
    sudo('ln -s /opt/pantheon/bcfg2 /var/lib/')
    sudo('cp /opt/pantheon/init/clients.xml /var/lib/bcfg2/Metadata/')
    sudo('sed -i "s/^plugins = .*$/plugins = Bundler,Cfg,Metadata,Packages,Probes,Rules,TGenshi\\nfilemonitor = gamin/" /etc/bcfg2.conf')
    sudo('/etc/init.d/bcfg2-server start')
    server_running = False
    while not server_running:
        with settings(warn_only = True):
            server_running = (sudo('netstat -atn | grep :6789')).rstrip('\n')
        sleep(5)
    sudo('/usr/sbin/bcfg2 -vqed') # @TODO: Add "-p 'mercury-aws'" for EC2

def initialize_drush():
    run('wget http://ftp.drupal.org/files/projects/drush-All-versions-3.0.tar.gz')
    run('tar xvzf drush-All-versions-3.0.tar.gz')
    run('sudo chmod 555 drush/drush')
    sudo('sudo chown -R root: drush')
    sudo('mv drush /opt/')
    sudo('ln -s /opt/drush/drush /usr/local/bin/drush')
    sudo('drush dl drush_make')

def initialize_pantheon():
    sudo('rm -rf /var/www')
    sudo('sudo drush make --working-copy /etc/mercury/mercury.make /var/www/')

def initialize_solr():
    run('wget http://apache.osuosl.org/lucene/solr/1.4.1/apache-solr-1.4.1.tgz')
    run('tar xvzf apache-solr-1.4.1.tgz')
    sudo('mkdir /var/solr')
    sudo('mv apache-solr-1.4.1/dist/apache-solr-1.4.1.war /var/solr/solr.war')
    sudo('mv apache-solr-1.4.1/example/solr /var/solr/default')
    sudo('mv /var/www/sites/all/modules/apachesolr/schema.xml /var/solr/default/conf/')
    sudo('mv /var/www/sites/all/modules/apachesolr/solrconfig.xml /var/solr/default/conf/')
    sudo('chown -R tomcat6:root /var/solr/')

def initialize_hudson():
    sudo('echo "hudson ALL = NOPASSWD: /usr/local/bin/drush, /etc/mercury/init.sh, /usr/bin/fab, /usr/sbin/bcfg2" >> /etc/sudoers')
    sudo('usermod -a -G shadow hudson')

def initialize_pressflow():
    sudo('mkdir /var/www/sites/default/files')
    sudo('cp /var/www/sites/default/default.settings.php /var/www/sites/default/settings.php')
    sudo('chown -R root:www-data /var/www/*')
    sudo('chown www-data:www-data /var/www/sites/default/settings.php')
    sudo('chmod 660 /var/www/sites/default/settings.php')
    sudo('chmod 775 /var/www/sites/default/files')

