# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import update
import time
import urllib2
import json
import traceback

from fabric.api import *

from pantheon import pantheon
from pantheon import jenkinstools

def configure():
    '''configure the Pantheon system.'''
    server = pantheon.PantheonServer()
    try:
        _test_for_previous_run()

        if pantheon.is_aws_server():
            _configure_ec2(server)

        if not pantheon.is_private_server():
            _check_connectivity(server)
            _configure_certificates()

        _configure_server(server)
        _configure_postfix(server)
        _restart_services(server)
        _configure_iptables(server)
        _configure_git_repo()
        _mark_incep(server)
        _report()
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'Configure')
        raise
    else:
        jenkinstools.junit_pass('Configure successful.', 'Configure')

def _test_for_previous_run():
    if os.path.exists("/etc/pantheon/incep"):
        abort("Pantheon config has already run. Exiting.")

def _configure_ec2(server):
    #lucid only for now...
    local('cp /opt/pantheon/bcfg2/TGenshi/mysql/apparmor/' + \
          'template.newtxt.G00_lucid /etc/apparmor.d/usr.sbin.mysqld')
    local('mkdir -p /mnt/mysql/tmp')
    local('chown -R root:root /mnt/mysql')
    local('chmod -R 777 /mnt/mysql')
    local('chown -R mysql:mysql /mnt/mysql/tmp')
    local('chmod -R 1777 /mnt/mysql/tmp')
    local('/etc/init.d/mysql stop')
    if(server.distro == 'centos'):
        local('mv /var/log/mysqld.log /mnt/mysql/')
        local('ln -s /mnt/mysql/mysqld.log /var/log/mysqld.log')
    else:
        local('mv /var/log/mysql /mnt/mysql/log')
        local('ln -s /mnt/mysql/log /var/log/mysql')
    local('mv /var/lib/mysql /mnt/mysql/lib')
    local('ln -s /mnt/mysql/lib /var/lib/mysql')
    local('/etc/init.d/varnish stop')
    local('mkdir /mnt/varnish')
    local('mv /var/lib/varnish /mnt/varnish/lib')
    local('ln -s /mnt/varnish/lib /var/lib/varnish')

def _check_connectivity(server):
    # Rackspace occasionally has connectivity issues unless a server gets
    # rebooted after initial provisioning.
    try:
        urllib2.urlopen('http://pki.getpantheon.com/', timeout=10)
        print 'Connectivity to the PKI server seems to work.'
    except urllib2.URLError, e:
        print "Connectivity error: ", e
        # Bail if a connectivity reboot has already been attempted.
        if os.path.exists("/etc/pantheon/connectivity_reboot"):
            abort("A connectivity reboot has already been attempted. Exiting.")
        # Record the running of a connectivity reboot.
        with open('/etc/pantheon/connectivity_reboot', 'w') as f:
            f.write('Dear Rackspace: Fix this issue.')
        local('sudo reboot')

def _configure_server(server):
    # Get any new packages.
    server.update_packages()
    # Update pantheon code, run bcfg2, restart jenkins.
    update.update_pantheon(first_boot=True)
    # Create the tunable files.
    local('cp /etc/pantheon/templates/tuneables /etc/pantheon/server_tuneables')
    local('chmod 755 /etc/pantheon/server_tuneables')

def _configure_certificates():
    # Just in case we're testing, we need to ensure this path exists.
    local('mkdir -p /etc/pantheon')

    pantheon.configure_root_certificate('http://pki.getpantheon.com')

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

    # Update BCFG2's client configuration to use the zone (a.k.a. OU) from the certificate
    local('sed -i "s/^bcfg2 = .*/bcfg2 = https:\/\/config.%s:6789/g" /etc/bcfg2.conf' % ou)

    # Wait 20 seconds so
    print 'Waiting briefly so slight clock skew does not affect certificate verification.'
    time.sleep(20)
    print local('openssl verify -verbose /etc/pantheon/system.crt')


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
    local("chmod g+s /var/git/projects")

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
