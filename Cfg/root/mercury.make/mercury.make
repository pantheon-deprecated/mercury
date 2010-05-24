core = 6.x

; Pressflow

projects[pressflow][type] = "core"
projects[pressflow][download][type] = bzr
projects[pressflow][download][url] = lp:pressflow

; Mercury
projects[mercury][type] = "profile"
projects[mercury][download][type] = "cvs"
projects[mercury][download][module] = "contributions/profiles/mercury/"
projects[mercury][download][revision] = "HEAD"

; Modules
projects[] = apachesolr
projects[memcache] = 1.5-rc1
projects[] = varnish

; ApacheSolr
libraries[SolrPhpClient][download][type] = "get"
libraries[SolrPhpClient][download][url] = "http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz"
libraries[SolrPhpClient][directory_name] = "SolrPhpClient"
libraries[SolrPhpClient][destination] = "modules/apachesolr"
