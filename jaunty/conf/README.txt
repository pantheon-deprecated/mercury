Ubuntu Jaunty Server specific config files.  

We recommend making a backup of the original config files before updating them with ours:

files listed in order needed as described on http://groups.drupal.org/node/25425/
Note: don't just move all the files at once - some dir's won't exists until after certain steps in the setup instructions.

mv sources.list /etc/apt/sources.list
mv ports.conf /etc/apache2/ports.conf
mv default /etc/apache2/sites-available/default
mv varnish.1 /etc/default/varnish (note file name change)
mv apc.ini /etc/php5/conf.d/apc.ini
mv default.vcl /etc/varnish/default.vcl
mv settings.php /var/www/sites/default/settings.php
mv tomcat6 /etc/default/tomcat6
mv solr.xml /etc/tomcat6/Catalina/localhost/solr.xml
mv server.xml /etc/tomcat6/server.xml
mv rc.local /etc/rc.local
mv init.sh /etc/mercury/init.sh
mv my.cnf /etc/mysql/my.cnf
mv varnish.2 /etc/default/varnish (note file name change)
