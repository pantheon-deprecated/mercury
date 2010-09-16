import os
import random
import string
import sys
import tempfile

from fabric.api import *

import pantheon

ENVIRONMENTS = ['dev','test','live']


def get_environments():
    """ Return list of development environments.
   
    """
    return ENVIRONMENTS


def _random_string(length):
    """ Create random string of ascii letters & digits.
    length: Int. Character length of string to return.

    """
    return ''.join(['%s' % random.choice (string.ascii_letters + \
                                          string.digits) \
                                          for i in range(length)])


class InstallTools:
    """ Generic Drupal installation helper functions.
    
    """

    def __init__(self, project, environment = 'dev', **kw):
        self.server = pantheon.PantheonServer()

        self.project = project
        self.environment = environment
        self.db_password = _random_string(10)
        self.destination = os.path.join(
                self.server.webroot,
                project,
                environment)


    def build_makefile(self, makefile, flags=['--working-copy']):
        """ Setup Drupal site using drush make
        makefile: full path to drush makefile
        flags: List. Optional: options to use with drush make.
               Defaults to ['--working-copy']

        """
        opts = ' '.join(['%s' % flag for flag in flags])
        local("rm -rf %s" % self.destination)
        local("drush make %s %s %s" % (opts, makefile, self.destination))


    def build_file_dirs(self, dirs=['sites/default/files']):
        """ Creates files directory within the Drupal installation.
        dirs: List. Optional: list of file directories to create.
              Defaults to ['sites/default/files'].
              All paths are relative to Drupal installation.

        """
        for file_dir in dirs:
            local("mkdir -p %s " % (os.path.join(self.destination, file_dir)))


    def build_gitignore(self, items=['sites/default/files/*',
                                     'sites/default/pantheon.settings.php',
                                     '!.gitignore']):
        """ Creates .gitignore entries.
        items: List. Optional: entries for .gitignore
              See function for default items.
              All paths are relative to Drupal installation.

        """
        with open(os.path.join(self.destination, '.gitignore'), 'w') as f:
            for item in items:
                f.write(item + '\n')


    def build_default_settings_file(self, site='default'):
        """ Copy default.settings.php to settings.php, and add an include
            to the pantheon.settings.php file
        Site: Optional. The drupal site name. Defaults to 'default'.

        """
        site_dir = os.path.join(self.destination, 'sites/%s/' % site)
        local("cp %s %s" % (site_dir + 'default.settings.php', site_dir + 'settings.php'))
        pantheon.add_default_settings_include(site_dir) 


    def build_pantheon_settings_file(self, site='default'):
        """ Setup the site settings.php
        site: Optional. The drupal site name. Defaults to 'default'.

        """
        site_dir = os.path.join(self.destination, 'sites/%s/' % site)
        settings = {'username': self.project,
                    'password': self.db_password,
                    'database': '%s_%s' % (self.project, self.environment),
                    'memcache_prefix': '%s_%s' % (self.project, self.environment)
                    'solr_path': '%s/%s' % (self.project, self.environment)}
        
        pantheon.create_pantheon_settings_file(site_dir, settings)


    def build_database(self, environments=get_environments()):
        """ Create a new database and set user grants (all).

        """
        username = self.project
        password = self.db_password

        for env in environments:      
            database = '%s_%s' % (self.project, env)
            local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
            local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS' %s" % (database))
            local("mysql -u root -e \"GRANT ALL ON %s.* TO '%s'@'localhost' \
                                      IDENTIFIED BY '%s';\"" % (database,
                                                                username, 
                                                                password))


    def build_solr_index():
        pass


    def build_vhost(self, environments=get_environments()):
        """ Create vhost files (for each developement environment).
        environments: Optional. List. 
                      Defaults to environments defined pantheon/pantheon.py 

        """
        for env in environments:
            vhost_dict = {'project':self.project
                          'environment':env}
            filename = '%s_%s' % (self.project, env)
            if env == 'live': 
                filename = '000_' + filename
            self.server.create_vhost(filename, vhost_dict)


    def build_drupal_cron():
        pass

