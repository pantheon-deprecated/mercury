#!/bin/bash
# To be launched at boot...
# Markers set at 50gb, 25gb, 15gb, 8gb, 4gb, 2gb, 1gb, and 512mb (rounded down)
# TODO: support for more distributions

# Get RAM size:
#RAM=$(grep MemTotal /proc/meminfo | sed 's/[^0-9]*//g')

RAM=16753487
if (($RAM>=50000000)); then
    APC_SIZE="16384"
    PHP_SIZE="8192M"
    TOMCAT_MAX_THREADS="6400"
    VARNISH_SIZE="32768M"
elif (($RAM>=25000000)); then
    APC_SIZE="8192"
    PHP_SIZE="4096M"
    TOMCAT_MAX_THREADS="3200"
    VARNISH_SIZE="16384M"
elif (($RAM>=15000000)); then
    APC_SIZE="4096"
    PHP_SIZE="2048M"
    TOMCAT_MAX_THREADS="1600"
    VARNISH_SIZE="8192M"
elif (($RAM>=8000000)); then
    APC_SIZE="2048"
    PHP_SIZE="1024M"
    TOMCAT_MAX_THREADS="800"
    VARNISH_SIZE="4096M"
elif (($RAM>=4000000)); then
    APC_SIZE="1024"
    PHP_SIZE="512M"
    TOMCAT_MAX_THREADS="400"
    VARNISH_SIZE="2048M"
elif (($RAM>=2000000)); then
    APC_SIZE="512"
    PHP_SIZE="256M"
    TOMCAT_MAX_THREADS="200"
    VARNISH_SIZE="1024M"
elif (($RAM>=1000000)); then
    APC_SIZE="256"
    PHP_SIZE="128M"
    TOMCAT_MAX_THREADS="100"
    VARNISH_SIZE="512M"
elif (($RAM>=500000)); then
    APC_SIZE="128"
    PHP_SIZE="128M"
    TOMCAT_MAX_THREADS="50"
    VARNISH_SIZE="256M"
else
    echo "under 512mb RAM not supported"
    exit 0
fi

# Get correct file paths:
RELEASE=$(grep CODENAME /etc/lsb-release | sed s/DISTRIB_CODENAME=//)

case $RELEASE in
    jaunty|karmic)
	APC_DIR="/etc/php5/conf.d/apc.ini"
	PHP_DIR="/etc/php5/apache2/php.ini"
	TOMCAT_DIR="/etc/tomcat6/server.xml"
	VARNISH_DIR="/etc/default/varnish"
	CLI_DIR="/etc/php5/cli/php.ini"
	;;
esac

sed --in-place=.bak "s/apc.shm_size=.*/apc.shm_size=${APC_SIZE}/" $APC_DIR
sed --in-place=.bak "s/memory_limit = .*;/memory_limit = ${PHP_SIZE};/g" $PHP_DIR
sed --in-place=.bak  s/maxThreads=\"[0-9]*\"/maxThreads=\"$TOMCAT_MAX_THREADS\"/ $TOMCAT_DIR
sed --in-place=.bak "s|-s file.*|-s file,/var/lib/varnish/\$INSTANCE/varnish_storage.bin,$VARNISH_SIZE\"|g" $VARNISH_DIR 
sed --in-place=.bak "s/memory_limit = .*;/memory_limit = 128M;/g" $CLI_DIR

#restart to get new configs:
/etc/init.d/apache2 restart
/etc/init.d/varnish restart
/etc/init.d/tomcat6 restartcase
