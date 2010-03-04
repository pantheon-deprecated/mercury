#/bin/bash

#This script updates the /var/lib/bcfg2 and /var/www/profiles dirs (mercury) from the pantheon project on launchpad and runs bcfg2 to apply the updates

echo "This script updates the /var/lib/bcfg2 and /var/www/profiles dirs (mercury) from the pantheon project on launchpad and runs bcfg2 to apply the updates"
echo "Continue? (y/n)"

read -n 1 ANSWER
echo ""
if [[ ${ANSWER} != "y" ]]; then
    echo "Cancelling....."
    exit 1
fi

# Create a log of all output we run.
echo "Creating a log of the output of this script at /root/update_mercury.log"
exec &> /root/update_mercury.log

#get any updates
cd /var/www/profiles; bzr ci -m "commited by mercury"; bzr merge --force; bzr commit -m "Mercury merged changes from Launchpad";
cd /var/lib/bcfg2; bzr ci -m "commited by mercury"; bzr merge --force; bzr commit -m "Mercury merged changes from Launchpad"

#process updates:
bcfg2 -vq

echo "done!"
