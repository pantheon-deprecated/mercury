import os
import random
import string
import sys
import tempfile

from pantheon import pantheon

from fabric.api import *

import pdb

def install_site(profile='Pantheon', project='pantheon'):
    """ Create a new Drupal installation.
    profile: installation type (e.g. pantheon/openatrium/aegir)
    
    """
    pdb.set_trace()
    # init_dict and build_dict can have addtional values added for new handlers.
    init_dict = {'project':project}
    build_dict = {}

    handler = _get_handler(profile)(**init_dict)
    handler.build(**build_dict)


def _get_handler(profile, module=sys.modules['__main__']):
    """ Return the handler for a particular profile. Defaults to PantheonProfile.
    profile: Supported installation types e.g: pantheon/openatrium/openpublish

    """
    subclass = profile + 'Profile'
    return hasattr(module, subclass) and \
           getattr(module, sublcass) or \
           PantheonProfile


"""

Additional profile handlers can be defined by creating a new class. e.g.:

class MIRProfile(NewSiteTools):
    def __init__(self, project, **kw):
        NewSiteTools.__init__(self, project, **kw)

    def build(self, **kw):
        # Step 1: create a working installation
        # Step 2: ??? 
        # Step 3: Make it rain.

"""

class NewSiteTools:
    """ Generic Drupal installation helper functions.
    
    """

    def __init__(self, project, environment = 'dev', **kw):
        self.server = pantheon.PantheonServer()

        self.project = project
        self.environment = environment
        self.db_password = self._random_string(10)
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
        opts = ' '.join(['%s'] % flag for flag in flags)
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


    def build_gitignore(self, items=['sites/default/files/*','!.gitignore']):
        """ Creates .gitignore entries.
        items: List. Optional: list of entries for .gitignore
              Defaults to ['sites/default/files/*', '!.gitignore'].
              All paths are relative to Drupal installation.

        """
        with open(os.path.join(self.destination, '.gitignore'), 'w') as f:
            for item in items:
                f.write(item + '\n')


    def build_settings_file(self, site='default'):
        """ Setup the site settings.php
        site: Optional. The drupal site name. Defaults to 'default'.

        """
        site_dir = os.path.join(self.destination, 'sites/%s/' % site)
        local("cp %s %s" % (site_dir + 'default.settings.php', site_dir + 'settings.php'))
        settings = {'username': self.project,
                    'password': self.db_password,
                    'database': '%s_%s_%s' % (project, environment, site),
                    'memcache_prefix': site + self._random_string(8)}
        pantheon.create_settings_file(site_dir, settings)


    def build_database(self, environments = ['dev','test','live']):
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


    def _random_string(length):
        """ Create random string of ascii letters & digits.
        length: Int. Character length of string to return.

        """
        return ''.join(['%s' % random.choice (string.ascii_letters + \
                                              string.digits) \
                                              for i in range(length)])

class PantheonProfile(NewSiteTools):

    def __init__(project, **kw):
        NewSiteTools.__init__(self, project, **kw)
  

    def build(self, **kw):
        makefile = '/opt/pantheon/fabric/templates/pantheon.make'

        self.build_makefile(makefile)
        self.build_file_dirs()
        self.build_gitignore()
        self.build_settings_file()
        self.build_database()
        self.server.create_solr_index(self.project)
        self.server.create_vhost(self.project)
        self.server.create_drupal_cron(self.project)



