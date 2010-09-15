import random
import string
import sys
import tempfile
import os

import pantheon

from fabric.api import *

"""Additional profile handlers can be defined by created a new class, with the at
least the following:

    class FooProfile(NewSiteTools):
        def __init__(self, project, environment):
            NewSiteTools.__init__(self, project, environment)

        def build(self):
            # Steps to create a working installation for this profile
"""


def get_handler(profile, module=sys.modules[newsite.__module__]):
    """ Return the handler for a particular profile. Defaults to PantheonProfile.
    profile: Supported installation types e.g: pantheon/openatrium/aegir

    """
    subclass = profile.capitalize() + 'Profile'
    return hasattr(module, subclass) and \
           getattr(module, sublcass)(**build_dict) or \
           PantheonProfile(**build_dict)


class PantheonProfile(NewSiteTools):

    def __init__(project, environment, **kw):
        NewSiteTools.__init__(self, project, environment)


    def build(self):
        makefile = os.path.join(pantheon.TEMPLATE_DIR, 'makefiles/pantheon.make')
        name = self.project + "_" + self.environment + "_default"

        self.build_makefile(makefile)
        self.build_file_dirs()
        self.build_gitignore()
        self.build_settings_file()
        self.build_database(self.project, name)
        self.server.build_solr_index(name)
        self.server.build_vhost()


class NewSiteTools():
    """ Generic Drupal installation helper functions.
    
    """

    def __init__(self, project, environment):
        self.server = pantheon.PantheonServer()

        self.project = project
        self.environment = environment
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
        opts = ''.join(['%s'] % flag for flag in flags)
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
        """ Creates .gitignore entires.
        items: List. Optional: list of entries for .gitignore
              Defaults to ['sites/default/files/*', '!.gitignore'].
              All paths are relative to Drupal installation.

        """
        with open(os.path.join(self.destination, '.gitignore'), 'w') as f:
            for item in items:
                f.write(item + '\n')


    def build_settings_file(self, site='default'):
        site_dir = os.path.join(self.destination, 'sites/%s/' % site)
        local("cp %s %s" % (site_dir + 'default.settings.php', site_dir + 'settings.php'))
        
        settings = {'username' = project,
                    'password' = self._random_string(10),
                    'database' = '%s_%s_%s' % (project, environment, site),
                    'memcache_prefix' = site + _random_string(8)}

        pantheon.create_settings_file(, settings, self.destination)


    def build_vhost(self):
        pass


    def build_database(self, username, database):
        password = ''.join(['%s' % random.choice(
                string.ascii_letters + string.digits) for i in range(10)])
        pantheon.create_database(database, username, password)

    def _random_string(length=10):
        return ''.join(['%s' % random.choice (string.ascii_letters + \
                                              string.digits) \
                                              for i in range(length)])
