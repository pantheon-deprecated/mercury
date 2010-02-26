#!/bin/bash

# These scripts run once on boot.

if [ -e /etc/mercury/incep ]; then
    exit 0
fi

# Create a bootlog of all output we run.
exec &> /etc/mercury/bootlog

# Get any updates.
cd /var/www/; bzr merge --force
cd /var/www/profiles; bzr merge --force
cd /var/lib/bcfg2; bzr merge --force

# Be sure we are running.
/etc/init.d/bcfg2-server start

# Wait for BCGF2 to spin up.
while [ "$CHECK" == "" ]; do
  CHECK=(`grep 'serving bcfg2-server' /var/log/syslog`)
  sleep 1
done

#a little more time...
sleep 60

# Process updates!
bcfg2 -vq

# Run the scripts!
for script in $( ls /etc/mercury/boot.d/S* ) ; do
  sh $script $*
done


# Mark incep date. This prevents us from ever running again.
echo `date` > /etc/mercury/incep

echo "Setup Complete!"