# Cacherouter: use APC for all local caching
$conf['cache_inc'] = './sites/all/modules/cacherouter/cacherouter.inc';
$conf['cacherouter'] = array(
  'default' => array(
    'engine' => 'apc',
    'shared' => FALSE,
    'prefix' => '',
    'static' => FALSE,
    'fast_cache' => TRUE,
  ),
);

# Varnish reverse proxy on localhost
$conf['reverse_proxy'] = TRUE;           
$conf['reverse_proxy_addresses'] = array('127.0.0.1'); 
