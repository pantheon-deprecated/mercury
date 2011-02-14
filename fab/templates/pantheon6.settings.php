<?php

$vhost_dir = '${vhost_root}';

/* Database settings */
if (isset($_SERVER['db_name'])) {
  $db_url = "mysqli://$_SERVER[db_username]:$_SERVER[db_password]@localhost/$_SERVER[db_name]";
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
    $db_url = "mysqli://$_SERVER[db_username]:$_SERVER[db_password]@localhost/$_SERVER[db_name]";
  }
}



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

/* Set SSL status so securepages.module will work. */
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] == 'https') {
  $_SERVER['HTTPS'] = 'on';
}
else {
  $_SERVER['HTTPS'] = '';
}