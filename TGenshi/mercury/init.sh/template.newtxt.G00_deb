#!/bin/bash

# These scripts run once on boot.

if [ -e /etc/mercury/incep ]; then
    /etc/init.d/mysql start
    exit 0
fi

# Create a bootlog of all output we run.
exec &> /etc/mercury/bootlog

# Get any updates.
cd /var/www/; bzr merge --force
cd /var/lib/bcfg2; bzr merge --force

# Be sure we are running.
/etc/init.d/bcfg2-server restart

# Wait for BCGF2 to spin up.
while [ -z "$(netstat -atn | grep :6789)" ]; do
    sleep 5
done

#a little more time...
echo "1 minute: BCFG2 is loading packages and config files";
sleep 60

# Process updates!
bcfg2-admin xcmd Packages.Refresh
bcfg2 -vqe

#get ready for possiby changing the mysql and varnish storage paths 
/etc/init.d/varnish stop

# Run the scripts!
for script in $( ls /etc/mercury/boot.d/S* ) ; do
  bash $script $*
done

#making sure varnish and mysql get's restarted...
/etc/init.d/mysql start
/etc/init.d/varnish start

echo "create database pressflow;" | mysql -u root

# Mark incep date. This prevents us from ever running again.
echo `date` > /etc/mercury/incep

echo '

##############################
#   Mercury Setup Complete!  #
##############################

'

echo '
DEAR SYSADMIN: MERCURY IS READY FOR YOU NOW

Do not forget the README.txt, CHANGELOG.txt and docs!
'| wall