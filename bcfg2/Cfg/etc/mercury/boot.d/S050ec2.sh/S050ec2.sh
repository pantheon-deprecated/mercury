#!/bin/bash

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

# Unset ssh key gen:
chmod -x /etc/init.d/ec2-ssh-host-key-gen
