core = 6.x

; Pressflow

projects[pressflow][type] = "core"
projects[pressflow][download][type] = bzr
projects[pressflow][download][url] = lp:pressflow

; Pantheon
projects[pantheon][type] = "profile"
projects[pantheon][download][type] = "cvs"
projects[pantheon][download][module] = "contributions/profiles/pantheon/"
projects[pantheon][download][revision] = "HEAD"

; Modules
projects[] = apachesolr
projects[] = memcache
projects[] = varnish

; ApacheSolr
libraries[SolrPhpClient][download][type] = "get"
libraries[SolrPhpClient][download][url] = "http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz"
libraries[SolrPhpClient][directory_name] = "SolrPhpClient"
libraries[SolrPhpClient][destination] = "modules/apachesolr"
