<?php

function get_project_and_environment() {
  $parts = explode('/', DRUPAL_ROOT);
  return array_slice($parts, -2, 2);
}

function get_vhost_file($project, $environment) {
  $vhost_dir = '/etc/apache2/sites-available/';
  if ($environment == 'live') {
    return $vhost_dir . '000_' . $project . '_' .$environment;
  }
  else {
    return $vhost_dir . $project . '_' . $environment;
  }
}

if (defined('DRUPAL_ROOT')) {
  // If DRUPAL_ROOT is set at this point, the request is coming from Drush.
  list($project, $environment) = get_project_and_environment();
  $vhost_file = get_vhost_file($project, $environment);
  $vhost = explode(PHP_EOL, file_get_contents($vhost_file));

  // Populate $_SERVER with values from vhost file.
  $vars = array();
  foreach ($vhost as $line) {
    $line = trim($line);
    if (strpos($line, 'SetEnv') !== FALSE) {
      $var = explode(' ', $line);
      $_SERVER[$var[1]] = $var[2];
    }
  }
}

// $_SERVER should now be populated from a Apache request or parsed from vhost for Drush request.
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

