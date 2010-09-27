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
    f = open('/etc/mailname', 'w')
    f.write(server.hostname)
    f.close()
    local('/usr/sbin/postconf -e "myhostname = %s"' % server.hostname)
    local('/usr/sbin/postconf -e "mydomain = %s"' % server.hostname)
    local('/usr/sbin/postconf -e "mydestination = %s"' % server.hostname)
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
    f = open('/etc/pantheon/incep', 'w')
    f.write(server.hostname)
    f.close()


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

def build_ldap_client(base_domain = "example.com", require_group = None, server_host = "auth.example.com"):
    """ Set permissions on project directory, settings.php, and files dir.
    environments: Optional. List.
    
    """
    if server_host == "auth.example.com":
        server_host = "auth." + base_domain
        
    # If necessary, restrict by group
    if require_group is not None:
        #local("sudo echo '-:ALL EXCEPT root sudo (" + require_group + "):ALL' | tee -a /etc/security/access.conf")
        local("sudo echo 'AllowGroups root sudo " + require_group + "' | tee -a /etc/ssh/sshd_config")
    else:
        local("sudo echo 'AllowGroups root sudo' | tee -a /etc/ssh/sshd_config")

    local("sudo /etc/init.d/ssh restart")
            
    ldap_domain = _fabuntu_ldap_domain_to_ldap(base_domain)
            
    local("sudo apt-get install -y debconf-utils")
            
    ldap_auth_conf_template = loader.load('ldap-auth-config.preseed.cfg', cls=TextTemplate)
    ldap_auth_conf = ldap_auth_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
    with NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_auth_conf)
        temp_file.seek(0)
        local("sudo debconf-set-selections " + temp_file.name)
        
    local("sudo apt-get install -y libnss-ldap ldap-auth-config")
        
    ldap_conf_template = loader.load('ldap.conf', cls=TextTemplate)
    ldap_conf = ldap_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
    with NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_conf)
        temp_file.seek(0)
        local("sudo cp " + temp_file.name + " /etc/ldap.conf")

    local("sudo auth-client-config -t nss -p lac_ldap")

def _fabuntu_ldap_domain_to_ldap(domain):
    parts = domain.split(".")
    ldap_domain_parts = []
    for part in parts:
        ldap_domain_parts.append("dc=" + part.lower())
    ldap_domain = ",".join(ldap_domain_parts)
    return ldap_domain
