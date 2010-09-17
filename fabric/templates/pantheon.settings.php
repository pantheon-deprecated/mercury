<?php

$db_url = 'mysqli://${username}:${password}@localhost/${database}';

$conf['pressflow_smart_start'] = TRUE;

/* Varnish */
$conf['reverse_proxy'] = TRUE;
$conf['reverse_proxy_addresses'] = array('127.0.0.1');

/* Apache Solr */
$conf['apachesolr_port'] = '8983';
$conf['apachesolr_path'] = '${solr_path}';

/* Memcached */
$conf['cache_inc'] = './sites/all/modules/memcache/memcache.inc';
$conf['memcache_servers'] = array(
         '127.0.0.1:11211' => 'default',
         );
$conf['memcache_bins'] = array(
          'cache' => 'default',
          );
$conf['memcache_key_prefix'] = '${memcache_prefix}';

