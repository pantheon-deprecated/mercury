#!/bin/bash

if [ -e /etc/mercury/incep ]; then
    exit 0
fi

exec &> /etc/mercury/bootlog

cd /var/www/; bzr merge --force

# Move mysql to /mnt
# TODO: this should be EBS'ed
mkdir /mnt/tmp
chown mysql:mysql /mnt/tmp/
chmod 777 /mnt/tmp
rsync -a /var/lib/mysql /mnt
/etc/init.d/mysql restart
# TODO: clean up vestigal /var/lib/mysql
    
# Move varnish to /mnt
rsync -a /var/lib/varnish /mnt
/etc/init.d/varnish restart
# TODO: clean up vistigal /var/lib/varnish

apt-get update   
apt-get -y upgrade
    
# Set up postfix

HOSTNAME=$(/usr/local/bin/ec2-metadata -p | sed 's/public-hostname: //')
echo $HOSTNAME > /etc/mailname
postconf -e 'myhostname = $hostname'
postconf -e 'mydomain = $hostname'
postconf -e 'mydestination = $hostname, localhost'
    
# Phone home
AMI=$(/usr/local/bin/ec2-metadata -a | sed 's/ami-id: //')
INSTANCE=$(/usr/local/bin/ec2-metadata -i | sed 's/instance-id: //')
curl "http://getpantheon.com/pantheon.php?ami=$AMI&instance=$INSTANCE"

# Mark incep date
echo `date` > /etc/mercury/incep
