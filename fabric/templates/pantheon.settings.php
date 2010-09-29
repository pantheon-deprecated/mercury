<?php

$db_url = "mysqli://$_SERVER[db_username]:$_SERVER[db_password]@localhost/$_SERVER[db_name]";

$conf['pressflow_smart_start'] = TRUE;

/* Varnish */
$conf['reverse_proxy'] = TRUE;
$conf['reverse_proxy_addresses'] = array('127.0.0.1');

/* Apache Solr */
$conf['apachesolr_port'] = '8983';
$conf['apachesolr_path'] = $_SERVER['solr_path'];

/* Memcached */
$conf['cache_inc'] = './sites/all/modules/memcache/memcache.inc';
$conf['memcache_servers'] = array(
         '127.0.0.1:11211' => 'default',
         );
$conf['memcache_bins'] = array(
          'cache' => 'default',
          );
$conf['memcache_key_prefix'] = $_SERVER['memcache_prefix'];

