# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import os

from pantheon import pantheon
import update

def configure(vps="none"):
    '''configure the Pantheon system.'''
    server = pantheon.PantheonServer()
    _test_for_previous_run()
    _configure_server(server)
    if (vps == "aws"):
        _config_ec2_(server)
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

def  _configure_ec2(server):
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
    # Pantheon Core
    local('git clone git://gitorious.org/pantheon/6.git /var/git/projects')
    # Drupal Core
    with cd('/var/git/projects'):
        local('git fetch git://gitorious.org/drupal/6.git master:drupal_core')
   
        local('git config receive.denycurrentbranch ignore')
    local('cp /opt/pantheon/fabric/templates/git.hook.post-receive /var/git/projects/.git/hooks/post-receive')    
    local('chmod +x /var/git/projects/.git/hooks/post-receive')


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

