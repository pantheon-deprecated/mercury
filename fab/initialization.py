# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import tempfile

from fabric.api import *

import update
from pantheon import pantheon

def initialize(vps=None):
    '''Initialize the Pantheon system.'''
    server = pantheon.PantheonServer()
    _initialize_server_type(vps)

    _initialize_fabric()
    _initialize_certificate()
    _initialize_package_manager(server)
    _initialize_bcfg2(server)
    _initialize_iptables(server)
    _initialize_drush()
    _initialize_solr(server)
    _initialize_sudoers(server)
    _initialize_hudson(server)
    _initialize_apache(server)
    _initialize_acl(server)

def init():
    '''Alias of "initialize"'''
    initialize()

def _initialize_server_type(vps):
    """Create a server type file if setting up a private server.

    """
    local('mkdir /etc/pantheon')
    if vps in ['aws', 'ebs', 'default']:
        server_type = '%s.server' % vps
        with open(os.path.join('/etc/pantheon', server_type), 'w') as f:
            f.write('Server type: %s' % server_type)

def _initialize_fabric():
    """Make symlink of /usr/local/bin/fab -> /usr/bin/fab.

    This is because using pip to install fabric will install it to
    /usr/local/bin but we want to maintaing compatibility with existing
    servers and hudson jobs.

    """
    if not os.path.exists('/usr/bin/fab'):
        local('ln -s /usr/local/bin/fab /usr/bin/fab')

def _initialize_certificate():
    """Install the Pantheon root certificate.

    """
    pantheon.configure_root_certificate('http://pki.getpantheon.com')

def _initialize_package_manager(server):
    """Setup package repos and version preferences.

    """
    if server.distro == 'ubuntu':
        with cd(server.template_dir):
            local('cp apt.pantheon.list /etc/apt/sources.list.d/pantheon.list')
            local('cp apt.php.pin /etc/apt/preferences.d/php')
            # No need for ldap patched ssh for non-getpantheon servers.
            if not pantheon.is_private_server():
                local('cp apt.openssh.pin /etc/apt/preferences.d/openssh')
            local('apt-key add apt.ppakeys.txt')
        local('echo \'APT::Install-Recommends "0";\' >>  /etc/apt/apt.conf')

    elif server.distro == 'centos':
        local('rpm -Uvh http://dl.iuscommunity.org/pub/ius/stable/Redhat/' + \
              '5/x86_64/ius-release-1.0-6.ius.el5.noarch.rpm')
        local('rpm -Uvh http://yum.fourkitchens.com/pub/centos/' + \
              '5/noarch/fourkitchens-release-5-6.noarch.rpm')
        local('rpm --import http://hudson-ci.org/redhat/hudson-ci.org.key')
        local('wget http://hudson-ci.org/redhat/hudson.repo -O ' + \
              '/etc/yum.repos.d/hudson.repo')
        local('yum -y install git17 --enablerepo=ius-testing')
        arch = local('uname -m').rstrip('\n')
        if (arch == "x86_64"):
            exclude_arch = "*.i?86"
        elif (arch == "i386" or arch == "i586" or arch == "i686"):
            exclude_arch = "*.x86_64"
        if exclude_arch:
            local('echo "exclude=%s" >> /etc/yum.conf' % exclude_arch)

    # Update package metadata and download packages.
    server.update_packages()

def _initialize_bcfg2(server):
    """Install bcfg2 client and run for the first time.

    """
    if server.distro == 'ubuntu':
        local('apt-get install -y gamin python-gamin python-genshi bcfg2')
    elif server.distro == 'centos':
        local('yum -y install bcfg2 gamin gamin-python python-genshi ' + \
              'python-ssl python-lxml libxslt')
    pantheon.copy_template('bcfg2.conf', '/etc/')
    # We use our own key/certs.
    local('rm -f /etc/bcfg2.key bcfg2.crt')
    # Run bcfg2
    local('/usr/sbin/bcfg2 -vqed', capture=False)

def _initialize_iptables(server):
    """Create iptable rules from template.

    """
    local('/sbin/iptables-restore < /etc/pantheon/templates/iptables')
    if server.distro == 'centos':
        local('cp /etc/pantheon/templates/iptables /etc/sysconfig/iptables')
        local('chkconfig iptables on')
        local('service iptables start')
    else:
        local('cp /etc/pantheon/templates/iptables /etc/iptables.rules')

def _initialize_drush():
    """Install Drush and Drush-Make.

    """
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

def _initialize_solr(server=pantheon.PantheonServer()):
    """Download Solr library and schema/config xml files from drupal module.

    """
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

def _initialize_sudoers(server):
    """Create placeholder sudoers files. Used for custom sudoer setup.

    """
    local('touch /etc/sudoers.d/003_pantheon_extra')
    local('chmod 0440 /etc/sudoers.d/003_pantheon_extra')

def _initialize_hudson(server):
    """Add hudson to ssl-cert group and restart hudson.

    """
    local('usermod -aG ssl-cert hudson')
    local('/etc/init.d/hudson restart')

def _initialize_apache(server):
    """Remove the default vhost and clear /var/www.

    """
    if server.distro == 'ubuntu':
        local('a2dissite default')
        local('rm -f /etc/apache2/sites-available/default*')
        local('rm -f /var/www/*')

def _initialize_acl(server):
    """Allow the use of ACLs and ensure they remain after reboot.

    """
    local('sudo tune2fs -o acl /dev/sda1')
    local('sudo mount -o remount,acl /')
    # For after restarts
    local('sudo sed -i "s/noatime /noatime,acl /g" /etc/fstab')

