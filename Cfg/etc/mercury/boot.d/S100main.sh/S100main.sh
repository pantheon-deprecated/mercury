#!/bin/bash

# Main/Global Boot Script

# Phone home - helps us to know how many users there are without passing any 
# identifying or personal information to us.
ID=`hostname | md5sum | sed 's/[^a-zA-Z0-9]//g'`
curl "http://getpantheon.com/pantheon.php?id=$ID&product=mercury"
