# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import os

from pantheon import *
from update import *

def configure(vps="none"):
    '''configure the Pantheon system.'''
    server = PantheonServer()
    _test_for_previous_run()
    _update_server()
    _setup_ec2_config() if (vps == "aws")
    _setup_main_config()
    _setup_postfix()
    _restart_services()
    _create_databases()
    _mark_incep()
    _report()

def _test_for_previous_run():
    if os.path.exists("/etc/pantheon/incep"):
        abort(Pantheon config has already run. Exiting.)

def _update_server():
    server.pmupdate()
    update_pressflow()
    update_pantheon()

def  _setup_ec2_config():
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

def _setup_main_config():
    local('cp /etc/pantheon/templates/tuneables /etc/pantheon/server_tuneables')
    local('chmod 755 /etc/pantheon/server_tuneables')
    if(server.distro == 'centos'):
        local('cp /etc/pantheon/templates/vhost/* /etc/httpd/conf/vhosts/')
    else:
        local('cp /etc/pantheon/templates/vhost/* /etc/apache2/sites-available/')
        local('ln -sf /etc/apache2/sites-available/pantheon_live /etc/apache2/sites-available/default')
        local('a2ensite pantheon_dev')
        local('a2ensite pantheon_test')
    local('/usr/sbin/usermod -a -G shadow hudson')

def _setup_postconf():
    if os.path.exists("/usr/local/bin/ec2-metadata"):
        hostname = local(/usr/local/bin/ec2-metadata -p | sed "s/public-hostname: //")
    else
    hostname = local('hostname')
    f = open('/etc/mailname', 'w')
    f.write(hostname)
    f.close()
    local('/usr/sbin/postconf -e myhostname = ' + hostname)
    local('/usr/sbin/postconf -e mydomain = ' + hostname)
    local('/usr/sbin/postconf -e mydestination = ' + hostname)
    local('/etc/init.d/postfix restart')

def _restart_services():
    local('/sbin/iptables-restore < /etc/pantheon/templates/iptables')
    server.restart_services()

def _create_databases():
# Create database
#if [ -n "$$MYSQL_ROOT_PASSWORD" ]; then
#  MYSQL_ROOT_PASSWORD="-p$${MYSQL_ROOT_PASSWORD}"
#fi
    local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS pantheon_dev'")
    local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS pantheon_test;'")
    local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS pantheon_live;'")

def _mark_incep():
    # Mark incep date. This prevents us from ever running again.
    f = open('/etc/pantheon/incep', 'w')
    f.write(hostname)
    f.close()

def _report():
    # Phone home - helps us to know how many users there are without passing any identifying or personal information to us.
    id = local(hostname -f | md5sum | sed "s/[^a-zA-Z0-9]//g"')
    local('curl "http://getpantheon.com/pantheon.php?id="' + id + '"&product=pantheon"')
    
    print('##############################')
    print('#   Pantheon Setup Complete! #')
    print('##############################')

    local('echo "DEAR SYSADMIN: PANTHEON IS READY FOR YOU NOW.  Do not forget the README.txt, CHANGELOG.txt and docs!" | wall')
