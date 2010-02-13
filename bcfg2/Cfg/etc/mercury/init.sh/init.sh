#!/bin/bash

if [ -e /etc/mercury/incep ]; then
    exit 0
fi

exec &> /etc/mercury/bootlog

cd /var/www/; bzr merge --force

# Move mysql and varnish to /mnt
# TODO support for EBS and RDS
/etc/init.d/mysql stop
/etc/init.d/varnish stop
mkdir -p /mnt/mysql/tmp
chown mysql:mysql /mnt/mysql/
chmod 777 /mnt/mysql/tmp
mkdir /mnt/varnish
mv /var/log/mysql /mnt/mysql/log
mv /var/lib/mysql /mnt/mysql/lib
mv /var/lib/varnish /mnt/varnish/lib
mkdir /mnt/varnish/lib/pressflow
chown varnish:varnish /mnt/varnish/lib/pressflow/
sed --in-place=.bak s*/tmp*/mnt/mysql/tmp* /etc/mysql/my.cnf
ln -s /mnt/mysql/log /var/log/mysql
ln -s /mnt/mysql/lib /var/lib/mysql
ln -s /mnt/varnish/lib /var/lib/varnish
/etc/init.d/mysql start
/etc/init.d/varnish start

# Update packages
apt-get update   
apt-get -y upgrade
    
# Config Memory
/etc/mercury/config_mem.sh

# Set up postfix
if [[-a /usr/local/bin/ec2-metadata ]]; then
    REAL_HOSTNAME=$(/usr/local/bin/ec2-metadata -p | sed 's/public-hostname: //')
    
    # Phone home
    AMI=$(/usr/local/bin/ec2-metadata -a | sed 's/ami-id: //')
    INSTANCE=$(/usr/local/bin/ec2-metadata -i | sed 's/instance-id: //')
    curl "http://getpantheon.com/pantheon.php?ami=$AMI&instance=$INSTANCE"
else
    REAL_HOSTNAME=`hostname`
fi

echo $REAL_HOSTNAME > /etc/mailname
postconf -e "myhostname = ${REAL_HOSTNAME}"
postconf -e "mydomain = ${REAL_HOSTNAME}"
postconf -e "mydestination = ${REAL_HOSTNAME}, localhost"
/etc/init.d/postfix restart
    
# Reset Drupal Admin Account
echo "DELETE FROM users WHERE uid = 1;ALTER TABLE users AUTO_INCREMENT = 1;" | mysql -u root -D pressflow

# Unset ssh key gen:
chmod -x /etc/init.d/ec2-ssh-host-key-gen

# Mark incep date
echo `date` > /etc/mercury/incep