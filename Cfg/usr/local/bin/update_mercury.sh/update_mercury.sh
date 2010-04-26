#!/bin/bash

#This script updates the /var/lib/bcfg2 rom the pantheon project on launchpad and runs bcfg2 to apply the updates

echo "This script updates the /var/lib/bcfg2 from the pantheon project on launchpad and runs bcfg2 to apply the updates"
echo -n "Continue? (y/n)"

read ANSWER
echo ""
if [[ ${ANSWER} != "y" ]]; then
    echo "Cancelling....."
    exit 1
fi

# Create a log of all output we run.
echo "Creating a log of the output of this script at /root/update_mercury.log"
exec &> /root/update_mercury.log

#get any updates
cd /var/lib/bcfg2; bzr ci -m "updates automatically commited by update_mercury.sh"; bzr merge; bzr commit -m "changes from Launchpad downloaded";

#process updates:
bcfg2 -vq

echo "done!"
