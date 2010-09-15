<?php

$db_url = 'mysqli://${username}:${password}@localhost/${database}';

/* Varnish */
$conf['reverse_proxy'] = TRUE;
$conf['reverse_proxy_addresses'] = array('127.0.0.1');

/* Memcached */
$conf['cache_inc'] = './sites/all/modules/memcache/memcache.inc';
$conf['memcache_servers'] = array(
         '127.0.0.1:11211' => 'default',
         );
$conf['memcache_bins'] = array(
          'cache' => 'default',
          );
$conf['memcache_key_prefix'] = '${memcache_prefix}';

