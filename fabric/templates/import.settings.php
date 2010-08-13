
##########################
#
# Mercury Settings
#
# Alter With Caution :)
#
##########################
$db_url = 'mysqli://${username}:${password}@localhost/${name}';

# Varnish reverse proxy on localhost
$conf['reverse_proxy'] = TRUE;
$conf['reverse_proxy_addresses'] = array('127.0.0.1');

# Memcached configuration
$conf['cache_inc'] = './sites/all/modules/memcache/memcache.inc';
$conf['memcache_servers'] = array(
         '127.0.0.1:11211' => 'default',
         );
$conf['memcache_bins'] = array(
          'cache'        => 'default',
          );
# Key Prefix: edit this for multisite use.
$conf['memcache_key_prefix'] = '${memcache_prefix}';

### END Mercury settings ###
