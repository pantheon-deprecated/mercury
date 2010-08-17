from fabric.api import *
from fabric.contrib.console import confirm
from time import sleep
from pantheon import 

def update_pantheon:
       '''Updating Pantheon from Launchpad'''
       sudo('/etc/init.d/bcfg2-server stop')
       sudo('cd /opt/pantheon; bzr up')
       sudo('/etc/init.d/bcfg2-server restart')
       server_running = False
       warn('Waiting for bcfg2 server to start')
       while not server_running:
              with settings(hide('warnings'), warn_only=True):
                     server_running = (sudo('netstat -atn | grep :6789')).rstrip('\n')
              sleep(5)
       sudo('/usr/sbin/bcfg2 -vq')
       '''Pantheon Updated'''

def update_pressflow(project = None, environment = None):
       '''Updating Pressflow'''
       if (project == None):
              print("No project selected. Using 'pantheon'")
              project = 'pantheon'
       if (environment == None):
              print("No environment selected. Using 'dev'")
              environment = 'dev'
       with('cd ' + server.webroot + '/' + project + '/' + environment):
              sudo('bzr up')
       '''Pressflow Updated'''

def update_data(source_project = None, source_environment = None, target_project = None, target_environment = None):
       source_temporary_directory = mkdtemp()
       target_temporary_directory = mkdtemp()
       webroot = PantheonServer().webroot

       if (project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (environment == None):
              print("No source_environment selected. Using 'live'")
              source_environment = 'live'
       if (project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       source_location = webroot + source_project + '_' + source_environment + "/"
       target_location = webroot + target_project + '_' + target_environment + "/"
       print('Exporting ' + source_project + '/' + source_environment + 'to temporary directory %s' % source_temporary_directory)
       _export_data(source_location, source_temporary_directory)
       print('Exporting ' + target_project + '/' + target_environment + 'to temporary directory %s' % target_temporary_directory)
       _export_data(target_location, target_temporary_directory)
       _setup_databases(target_project)

#def update_code():
#def update_files():

def _export_data(webroot, temporary_directory):
    sites = DrupalInstallation(webroot).get_sites()
    with cd(temporary_directory + "/htdocs"):
        exported = list()
        for site in sites:
            if site.valid:
                # If multiple sites use same db, only export once.
                if site.database.name not in exported:
                    local("mysqldump --single-transaction --user='%s' --password='%s' --host='%s' %s >
 %s.sql" % \
                      ( site.database.username, 
                        site.database.password, 
                        site.database.hostname, 
                        site.database.name,
                        site.database.name,
                      )    
                    )
                    exported.append(site.database.name)

def _setup_databases(archive):
    # Sites are matched to databases. Replace database name with: "project_environment_sitename"
    names = list()
    for site in archive.sites:
        # MySQL allows db names up to 64 chars. Check for & fix name collisions, assuming: 
        # project (up to 16chars) and environment (up to 5chars).
        for length in range(43,0,-1):
            #TODO: Write better fix for collisions
            name = archive.project + '_' + archive.environment + '_' + \
                    site.get_safe_name()[:length] + \
                    str(random.randint(0,9))*(43-length)
            if name not in names:
                break
            if length == 0:
                abort("Database name collision")
        site.database.name = name
        names.append(name)
   
    # Create databases. If multiple sites use same db, only create once.
    databases = set([site.database.name for site in archive.sites])
    for database in databases:
        local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
        local("mysql -u root -e 'CREATE DATABASE %s'" % (database))

    # Create temporary superuser to perform import operations
    with settings(warn_only=True):
        local("mysql -u root -e \"CREATE USER 'pantheon-admin'@'localhost' IDENTIFIED BY '';\"")
    local("mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'pantheon-admin'@'localhost' WITH GRANT OPTION;\"")

    for site in archive.sites:
        # Set grants
        local("mysql -u pantheon-admin -e \"GRANT ALL ON %s.* TO '%s'@'localhost' IDENTIFIED BY '%s';\"" % \
                (site.database.name, site.database.username, site.database.password))

        # Strip cache tables, convert MyISAM to InnoDB, and import.
        local("cat %s | grep -v '^INSERT INTO `cache[_a-z]*`' | \
                grep -v '^INSERT INTO `ctools_object_cache`' | \
                grep -v '^INSERT INTO `watchdog`' | \
                grep -v '^INSERT INTO `accesslog`' | \
                grep -v '^USE `' | \
                sed 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' | \
                mysql -u pantheon-admin %s" % \               
              (archive.location + site.database.dump, site.database.name))
        
    # Cleanup
        local("mysql -u pantheon-admin -e \"DROP USER 'pantheon-admin'@'localhost'\"")
        with cd(archive.location):
               local("rm -f *.sql")
