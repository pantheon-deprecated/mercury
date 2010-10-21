# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import os


from pantheon import pantheon
import update
import time
import urllib2
import json


def configure(vps="none"):
    '''configure the Pantheon system.'''
    server = pantheon.PantheonServer()
    _configure_server(server)
    _check_connectivity()
    _test_for_previous_run()
    _test_for_private_server(server)
    if (vps == "aws"):
        _configure_ec2(server)
    _configure_postfix(server)
    _restart_services(server)
    _configure_iptables(server)
    _configure_git_repo()
    _mark_incep(server)
    _report()


def _test_for_previous_run():
    if os.path.exists("/etc/pantheon/incep"):
        abort("Pantheon config has already run. Exiting.")


def _configure_server(server):
    server.update_packages()
    update.update_pantheon()
    local('cp /etc/pantheon/templates/tuneables /etc/pantheon/server_tuneables')
    local('chmod 755 /etc/pantheon/server_tuneables')


# The Rackspace Cloud occasionally has connectivity issues unless a server gets
# rebooted after initial provisioning.
def _check_connectivity():
    try:
        urllib2.urlopen('http://pki.getpantheon.com/', timeout=10)
        print 'Connectivity to the PKI server seems to work.'
    except urllib2.URLError, e:
        print "Connectivity error: ", e
        # Bail if a connectivity reboot has already been attempted.
        if os.path.exists("/etc/pantheon/connectivity_reboot"):
            abort("A Pantheon connectivity reboot has already been attempted. Exiting.")
        # Record the running of a connectivity reboot.
        with open('/etc/pantheon/connectivity_reboot', 'w') as f:
            f.write('Dear Rackspace: Fix this issue.')
        local('sudo reboot')


def _test_for_private_server(server):
    try:
        urllib2.urlopen('http://pki.getpantheon.com/info', timeout=10)
        print 'Appears to be a getpantheon.com server'
        _configure_certificates()
        _initialize_support_account(server)
    except urllib2.URLError, e:
        print 'Appears to be a private server - skipping getpantheon.com-specific functions'


def _configure_certificates():
    # Just in case we're testing, we need to ensure this path exists.
    local('mkdir -p /etc/pantheon')

    # Set the Helios CA server to use.
    pki_server = 'http://pki.getpantheon.com'

    # Download and install the root CA.
    local('curl %s | sudo tee /usr/share/ca-certificates/pantheon.crt' % pki_server)
    local('echo "pantheon.crt" | sudo tee -a /etc/ca-certificates.conf')
    #local('cat /etc/ca-certificates.conf | sort | uniq | sudo tee /etc/ca-certificates.conf') # Remove duplicates.
    local('sudo update-ca-certificates')

    # Now Helios cert is OTS
    pki_server = 'https://pki.getpantheon.com'

    # Ask Helios about what to put into the certificate request.
    host_info = json.loads(urllib2.urlopen('%s/info' % pki_server).read())
    ou = host_info['ou']
    cn = host_info['cn']
    subject = '/C=US/ST=California/L=San Francisco/O=Pantheon Systems, Inc./OU=%s/CN=%s/emailAddress=hostmaster@%s/' % (ou, cn, cn)

    # Generate a local key and certificate-signing request.
    local('openssl genrsa 4096 > /etc/pantheon/system.key')
    local('chmod 600 /etc/pantheon/system.key')
    local('openssl req -new -nodes -subj "%s" -key /etc/pantheon/system.key > /etc/pantheon/system.csr' % subject)

    # Have the PKI server sign the request.
    local('curl --silent -X POST -d"`cat /etc/pantheon/system.csr`" %s > /etc/pantheon/system.crt' % pki_server)

    # Combine the private key and signed certificate into a PEM file (for Apache and Pound).
    local('cat /etc/pantheon/system.crt /etc/pantheon/system.key > /etc/pantheon/system.pem')
    local('chmod 640 /etc/pantheon/system.pem')
    local('chgrp ssl-cert /etc/pantheon/system.pem')

    # Start pound, which has been waiting for system.pem
    local('/etc/init.d/pound start');

    # Wait 20 seconds so
    print 'Waiting briefly so slight clock skew does not affect certificate verification.'
    time.sleep(20)
    print local('openssl verify -verbose /etc/pantheon/system.crt')


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
        local('cp /opt/pantheon/fabric/templates/authorized_keys .ssh/')
        #local('cat ~/.ssh/id_rsa.pub > .ssh/authorized_keys')
        local('chmod 600 .ssh/authorized_keys')
        local('chown -R pantheon: .ssh')


def _configure_ec2(server):
    local('chmod 1777 /tmp')
    if(server.distro == 'centos'):
        local('mv /var/log/mysqld.log /mnt/mysql/')
        local('ln -s /mnt/mysql/mysqld.log /var/log/mysqld.log')
    else:
        local('mv /var/log/mysql /mnt/mysql/log')
        local('ln -s /mnt/mysql/log /var/log/mysql')
    local('mv /var/lib/mysql /mnt/mysql/lib')
    local('ln -s /mnt/mysql/lib /var/lib/mysql')
    local('/etc/init.d/varnish stop')
    local('mv /var/lib/varnish /mnt/varnish/lib')
    local('ln -s /mnt/varnish/lib /var/lib/varnish')
    local('chown varnish:varnish /mnt/varnish/lib/pressflow/')


def _configure_postfix(server):
    hostname = server.get_hostname()
    with open('/etc/mailname', 'w') as f:
        f.write(hostname)
    local('/usr/sbin/postconf -e "myhostname = %s"' % hostname)
    local('/usr/sbin/postconf -e "mydomain = %s"' % hostname)
    local('/usr/sbin/postconf -e "mydestination = %s"' % hostname)
    local('/etc/init.d/postfix restart')


def _restart_services(server):
    server.restart_services()


def _configure_iptables(server):
    if server.distro == 'centos':
        local('sed -i "s/#-A/-A/g" /etc/sysconfig/iptables')
        local('/sbin/iptables-restore < /etc/sysconfig/iptables')
    else:
        local('sed -i "s/#-A/-A/g" /etc/iptables.rules')
        local('/sbin/iptables-restore </etc/iptables.rules')


def _configure_git_repo():
    if os.path.exists('/var/git/projects'):
        local('rm -rf /var/git/projects')
    local('mkdir -p /var/git/projects')
    # Set GID
    local("chmod g+s /var/git/projects")
    # Pantheon Core
    local('git clone git://gitorious.org/pantheon/6.git /var/git/projects/pantheon')
    # Drupal Core
    with cd('/var/git/projects/pantheon'):
        local('git fetch git://gitorious.org/drupal/6.git master:drupal_core')

        local('git config receive.denycurrentbranch ignore')
        local('git config core.sharedRepository group')
    local('cp /opt/pantheon/fabric/templates/git.hook.post-receive /var/git/projects/pantheon/.git/hooks/post-receive')
    local('chmod +x /var/git/projects/pantheon/.git/hooks/post-receive')


def _mark_incep(server):
    '''Mark incep date. This prevents us from ever running again.'''
    hostname = server.get_hostname()
    with open('/etc/pantheon/incep', 'w') as f:
        f.write(hostname)


def _report():
    '''Phone home - helps us to know how many users there are without passing \
    any identifying or personal information to us.

    '''
    id = local('hostname -f | md5sum | sed "s/[^a-zA-Z0-9]//g"').rstrip('\n')
    local('curl "http://getpantheon.com/pantheon.php?id="' + id + '"&product=pantheon"')

    print('##############################')
    print('#   Pantheon Setup Complete! #')
    print('##############################')

    local('echo "DEAR SYSADMIN: PANTHEON IS READY FOR YOU NOW.  Do not forget the README.txt, CHANGELOG.txt and docs!" | wall')

