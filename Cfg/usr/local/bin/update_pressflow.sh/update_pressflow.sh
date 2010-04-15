#!/bin/bash

#This script updates the /var/www dir (pressflow) from the pressflow project on launchpad

echo "This script updates the /var/www dir (pressflow) from the pressflow project on launchpad"
echo -n "Continue? (y/n)"

read ANSWER
echo ""
if [[ ${ANSWER} != "y" ]]; then
    echo "Cancelling....."
    exit 1
fi

# Create a log of all output we run.
echo "Creating a log of the output of this script at /root/update_pressflow.log"
exec &> /root/update_pressflow.log

#get any updates
cd /var/www/; bzr ci -m "updates automatically commited by update_pressflow.sh"; bzr merge --force; bzr commit -m "changes from pressflow repo downloaded";

echo "done!"
