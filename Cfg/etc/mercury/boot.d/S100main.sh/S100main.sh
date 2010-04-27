#!/bin/bash

# Main/Global Boot Script

#copy template to root, rename and make executable
cp /etc/mercury/MERCURY_TEMPLATE /root/MERCURY_TUNEABLES
chown 755 /root/MERCURY_TUNEABLES

# Phone home - helps us to know how many users there are without passing any 
# identifying or personal information to us.
ID=`hostname -f | md5sum | sed 's/[^a-zA-Z0-9]//g'`
curl "http://getpantheon.com/pantheon.php?id=$ID&product=mercury"
