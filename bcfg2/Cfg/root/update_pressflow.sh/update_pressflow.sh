#/bin/bash

#This script updates the /var/www dir (pressflow) from the pressflow project on launchpad

echo "This script updates the /var/www dir (pressflow) from the pressflow project on launchpad"
echo "Continue? (y/n)"

read -n 1 ANSWER
if [[ ${ANSWER} != "y" ]]; then
    echo "Cancelling....."
    exit 1
fi

# Create a bootlog of all output we run.
exec &> /root/update_pressflow.log

#get any updates
cd /var/www/; bzr merge --force

echo "done!"
