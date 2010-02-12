
# Varnish reverse proxy on localhost
$conf['reverse_proxy'] = TRUE;           
$conf['reverse_proxy_addresses'] = array('127.0.0.1'); 

# Memcached configuration - uncomment to use Memcached instead of Cacherouter:
$conf = array(
   'cache_inc' => './sites/all/modules/memcache/memcache.db.inc',
   'memcache_servers' => array(
      			 '127.0.0.1:11211' => 'default',
  			 '127.0.0.1:11212' => 'block',
  			 '127.0.0.1:11213' => 'filter',
  			 '127.0.0.1:11214' => 'form',
  			 '127.0.0.1:11215' => 'menu',
  			 '127.0.0.1:11216' => 'page',
  			 '127.0.0.1:11217' => 'updates',
  			 '127.0.0.1:11218' => 'views',
  			 '127.0.0.1:11219' => 'content',
			 ),
   'memcache_bins' => array(
			    'cache'        => 'default',
			    'cache_block'  => 'block',
			    'cache_filter' => 'filter',
			    'cache_form'   => 'form',
			    'cache_menu'   => 'menu',
			    'cache_page'   => 'page',
			    'cache_update' => 'update',
		   ),
);

# Cacherouter configuration  - uncomment to use Cacherouter instead of Memcached:
#$conf['cache_inc'] = './sites/all/modules/cacherouter/cacherouter.inc';
#$conf['cacherouter'] = array(
#  'default' => array(
#    'engine' => 'apc',
#    'shared' => FALSE,
#    'prefix' => '',
#    'static' => FALSE,
#    'fast_cache' => TRUE,
#  ),
#);

