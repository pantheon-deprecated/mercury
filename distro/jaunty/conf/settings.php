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

# memcached configuration:
#$conf = array(
#   'cache_inc' => './sites/all/modules/memcache/memcache.db.inc',
#   'memcache_servers' => array(
#      			 '127.0.0.1:11211' => 'default',
#  			 '127.0.0.1:11212' => 'default',
#  			 '127.0.0.1:11213' => 'default',
#  			 '127.0.0.1:11214' => 'default',
#  			 '127.0.0.1:11215' => 'page',
#  			 '127.0.0.1:11216' => 'page',
#  			 '127.0.0.1:11217' => 'filter',
#  			 '127.0.0.1:11218' => 'filter',
#			 ),
#   'memcache_bins' => array(
#   		   'cache'        => 'default', 
#		   'cache_menu'   => 'default',
#		   'cache_page'   => 'page',
#		   'cache_filter' => 'filter',
#		   ),
#);
