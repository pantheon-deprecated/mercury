<?php

$databases = array (
  'default' =>
  array (
    'default' =>
    array (
      'database' => $_SERVER['db_name'],
      'username' => $_SERVER['db_username'],
      'password' =>  $_SERVER['db_password'],
      'host' => 'localhost',
      'port' => '',
      'driver' => 'mysql',
      'prefix' => '',
    ),
  ),
);

$conf['pressflow_smart_start'] = TRUE;

/* Apache Solr */
$conf['apachesolr_default_server'] = $_SERVER['db_name'];

/* Memcached */
include_once(DRUPAL_ROOT . '/includes/cache.inc');
include_once(DRUPAL_ROOT . '/sites/all/modules/memcache/memcache.inc');
$conf['cache_default_class'] = 'MemCacheDrupal';
$conf['memcache_key_prefix'] = $_SERVER['memcache_prefix'];

/* Varnish */
$conf['reverse_proxy'] = TRUE;
$conf['reverse_proxy_addresses'] = array('127.0.0.1');
$conf['page_cache_invoke_hooks'] = FALSE;

