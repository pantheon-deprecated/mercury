#!/bin/bash

# Move mysql and varnish to /mnt
# TODO support for EBS and RDS

#mysql:
/etc/init.d/mysql stop
mkdir -p /mnt/mysql/tmp
chown mysql:mysql /mnt/mysql/
chmod 777 /mnt/mysql/tmp
mv /var/log/mysql /mnt/mysql/log
ln -s /mnt/mysql/log /var/log/mysql
mv /var/lib/mysql /mnt/mysql/lib
ln -s /mnt/mysql/lib /var/lib/mysql
/etc/init.d/mysql start

#varnish:
/etc/init.d/varnish stop
mkdir /mnt/varnish
mv /var/lib/varnish /mnt/varnish/lib
ln -s /mnt/varnish/lib /var/lib/varnish
chown varnish:varnish /mnt/varnish/lib/pressflow/
/etc/init.d/varnish start

# Unset ssh key gen:
chmod -x /etc/init.d/ec2-ssh-host-key-gen
