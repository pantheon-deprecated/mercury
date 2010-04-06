#!/bin/bash
# Get System RAM size for varnish, tomcat, apc, php and memcached Probes

RAM=$(grep MemTotal /proc/meminfo | sed 's/[^0-9]*//g')

if (($RAM>=50000000)); then
    echo "50GB"
elif (($RAM>=25000000)); then
    echo "25GB"
elif (($RAM>=15000000)); then
    echo "15GB"
elif (($RAM>=8000000)); then
    echo "8GB"
elif (($RAM>=4000000)); then
    echo "4GB"
elif (($RAM>=2000000)); then
    echo "2GB"
elif (($RAM>=1000000)); then
    echo "1GB"
else
    echo "500MB"
fi