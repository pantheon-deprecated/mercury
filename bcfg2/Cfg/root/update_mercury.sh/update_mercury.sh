#/bin/bash

#This script updates the /var/lib/bcfg2 and /var/www/profiles dirs (mercury) from the pantheon project on launchpad

echo "This script updates the /var/lib/bcfg2 and /var/www/profiles dirs (mercury) from the pantheon project on launchpad"
echo "Continue? (y/n)"

read -n 1 ANSWER
if [[ ${ANSWER} != "y" ]]; then
    echo "Cancelling....."
    exit 1
fi

# Create a log of all output we run.
echo "Creating a log of the output of this script at /root/update_mercury.log"
&> /root/update_mercury.log

#get any updates
cd /var/www/profiles; bzr merge --force
cd /var/lib/bcfg2; bzr merge --force

#process updates:
bcfg2 -vq

echo "done!"
