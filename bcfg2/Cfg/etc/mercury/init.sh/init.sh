#!/bin/bash

# These scripts run once on boot.

if [ -e /etc/mercury/incep ]; then
    exit 0
fi

exec &> /etc/mercury/bootlog

# Run the scripts!
for script in $( ls /etc/mercury/boot.d/S* ) ; do
  sh $script $*
done


# Mark incep date
echo `date` > /etc/mercury/incep
