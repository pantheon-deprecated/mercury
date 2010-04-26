#!/bin/bash

#Use this file to set variables in config files rather than editing the config file directly.  
#This allows BCFG2 to use your values rather than replacing the file with our defaults.
#Any variable not set in this file (ie, left empty) receives the default value (often based on system memory size)

export APACHE_MAXCLIENTS=""
export APC_MEMORY=""
export INNODB_BUFFER_POOL=""
export KEY_BUFFER=""
export MEMCACHED_MEMORY=""
export PHP_MEMORY=""
export TOMCAT_MAX_THREADS=""
export TOMCAT_MEMORY=""
export VARNISH_MEMORY=""
export VARNISH_VCL_ERROR=""
export VARNISH_VCL_FETCH=""
export VARNISH_VCL_HASH=""
export VARNISH_VCL_RECV=""
