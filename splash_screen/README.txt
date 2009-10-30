MERCURY 0.7-Beta created by Chapter Three (http://chapterthree.com)                                  10/29/09

Thank you for using this AMI.  Please post any question/comments to http://groups.drupal.org/pantheon/

To finish configuring your Pressflow install:

1) change the default Pressflow administrator password (and add your email address):
My account -> Edit

2) set the mysql root password and create a non-root account (changing user and password to appropriate values):
mysql -u root
mysql> set password for root@localhost=PASSWORD('new_password');
mysql> grant all on pressflow.* to user@localhost identified by 'password';
mysql> flush privileges;
mysql> \q

3) update your Pressflow install with the new mysql account information by editing 
/var/www/pressflow/sites/default/settings.php (again using the appropriate username and password values):

nano -w /var/www/pressflow/sites/default/settings.php 

and change: 
$db_url = 'mysqli://root:@localhost/pressflow';
to:
$db_url = 'mysqli://new_user:new_password@localhost/pressflow';

4) update the site name and email address:
Administer -> Site configuration -> Site information

5) make Pressflow the default page rather than our splash page by changing /etc/apache2/sites-available/default
and replacing all occurences of /var/www with /var/www/pressflow

nano -w /etc/apache2/sites-available/default
/etc/init.d/apache2 restart

6) add content!

Note: for space reasons, a default Mercury install stores mysql data on /mnt.  This data does not get backed up 
by an AMI backup and it will disappear if your AMI is stopped or crashes.  Make backups of /mnt/mysql on a regular 
basis (and/or move it to an EBS volume).
