<?php

$vhost_dir = '${vhost_root}';

/* Database settings */
if (isset($_SERVER['db_name'])) {
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
}
elseif (is_file($vhost_dir .'000_${project}_live') ||
        is_file($vhost_dir .'${project}_dev') ||
        is_file($vhost_dir .'${project}_test')) {

  // Determine wether or not drupal_root was specified as a cli option.
  if(drush_get_option('root')) {
    $drupal_root = drush_get_option('root');
  }
  elseif (drush_get_option('r')) {
    $drupal_root = drush_get_option('r');
  }
  else {
    $drupal_root = $_SERVER['PWD'];
  }

  // Get settings.php variables from vhost file.
  if (preg_match('/${project}\/live/', $drupal_root)) {
    $vhost = explode(PHP_EOL, file_get_contents($vhost_dir .'000_${project}_live'));
  }
  elseif (preg_match('/${project}\/dev/', $drupal_root)) {
    $vhost = explode(PHP_EOL, file_get_contents($vhost_dir .'${project}_dev'));
  }
  elseif (preg_match('/${project}\/test/', $drupal_root)) {
    $vhost = explode(PHP_EOL, file_get_contents($vhost_dir .'${project}_test'));
  }
  if (isset($vhost)) {
    $vars = array();
    foreach ($vhost as $line) {
      $line = trim($line);
      if (strpos($line, 'SetEnv') !== FALSE) {
        $var = explode(' ', $line);
        $_SERVER[$var[1]] = $var[2];
      }
    }
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
  }
}

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

