MERCURY 1.1 Beta created by Chapter Three (http://chapterthree.com)                                  04/13/10

On first boot, please give the bcfg2 server up to 2 minutes to spin up and make sure the system is up to date.
You can monitor the progress with "tail -f /etc/mercury/bootlog".
Once you see "Setup Complete!", you can go to the the url of your site and configure pressflow.
For the best performance, choose the "Mercury" profile
The Database is called default, the username is root and there is no password (for now - see #1 below)
To finish configuring your Pressflow install:

1) set the mysql root password and create a non-root account (changing user and password to appropriate values):
mysql -u root
mysql> set password for root@localhost=PASSWORD('new_password');
mysql> grant all on default.* to user@localhost identified by 'password';
mysql> flush privileges;
mysql> \q

2) update your Pressflow install with the new mysql account information by editing 
/var/www/sites/default/settings.php (again using the appropriate username and password values):

nano -w /var/www/sites/default/settings.php 

and change: 
$db_url = 'mysqli://root:@localhost/default';
to:
$db_url = 'mysqli://new_user:new_password@localhost/default';

3) add content!

Note: for space reasons, a default Mercury install (on AWS) stores mysql data on /mnt.  This data does not get backed
up by an AMI backup and it will disappear if your AMI is stopped or crashes.  Make backups of /mnt/mysql on a regular 
basis (and/or move it to an EBS volume).  If you choose to move /mnt/mysql on an Ubuntu Lucid server, you'll need to 
update the APPARMOR_MYSQLD vaiable in the tuneables file (see: http://groups.drupal.org/node/70258).

We have docs online that describe how to configure/tune Mercury (http://groups.drupal.org/node/70258) and setup Mercury 
to use multi-site (http://groups.drupal.org/node/72488)

Please post any question/comments to http://groups.drupal.org/pantheon/

Thanks and enjoy the speed of Mercury!
