import os
import random
import string
import sys
import tempfile

from fabric.api import *

import pantheon
from project import project

def _drush_download(modules):
    """ Download list of modules using Drush.
    modules: list of module names.

    """
    #TODO: temporary until integrated in pantheon repo
    for module in modules:
         local('drush -y dl %s' % module)

class InstallTools(project.BuildTools):

    def __init__(self, project, **kw):
        """ Initialize generic installation object & helper functions.
        project: the name of the project to be built.

        """
        project.BuildTools.__init__(self, project)

        self.working_dir = tempfile.mkdtemp()
        self.destination = os.path.join(self.server.webroot, project)
        self.author = 'Hudson User <hudson@pantheon>'
        self.db_password = pantheon.random_string(10)

    def build_project_branch(self):
        """ Bring master up to date and create a new project branch.

        """
        with cd('/var/git/projects/%s' % self.project):
            local('git pull origin master')
            with settings(hide('warnings'), warn_only=True):
                local('git tag -d %s.initialization' % self.project)
                local('git branch -D %s' % self.project)
            local('git branch %s' % self.project)

    def build_working_dir(self):
        """ Clone project to a temporary working directory.

        """
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              self.working_dir))

    def build_project_modules(self, modules=['apachesolr','memcache','varnish']):
        """ Add required modules to project branch.
        modules: Optional list of modules. Defaults to:
                 apachesolr, memcache, varnish

        """
        #TODO: temporary until integrated in pantheon repo.
        module_dir = os.path.join(self.working_dir, 'sites/all/modules')
        local('mkdir %s' % module_dir)
        with cd(module_dir):
            _drush_download(modules)
        with cd(self.working_dir):
            local('git add -A .')
            local("git commit --author=\"%s\" -m 'Add required modules'" % self.author)

    def build_project_libraries(self):
       """ Add code libraries to project.

       """
       #TODO: temporary until integrated in pantheon repo
       dest = os.path.join(self.working_dir, 'sites/all/modules/apachesolr/')
       with cd(dest):
           local('wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz')
           local('tar xzf SolrPhpClient.r22.2009-11-09.tgz')
           local('rm -f SolrPhpClient.r22.2009-11-09.tgz')
       with cd(self.working_dir):
           local('git add -A .')
           local("git commit --author=\"%s\" -m 'Add required libraries'" % self.author)

    def build_makefile(self, makefile):
        """ Setup Drupal site using drush make
        makefile: full path to drush makefile

        """
        tempdir = tempfile.mkdtemp()
        local('rm -rf %s' % tempdir)
        local("drush make %s %s" % (makefile, tempdir))
        local('rm -rf %s/*' % self.working_dir)
        local('rsync -av %s/* %s' % (tempdir, self.working_dir))
        with cd(self.working_dir):
            local('git add -A .')
            local("git commit --author=\"%s\" -m 'Site from makefile'" % self.author)
        local('rm -rf %s' % tempdir)

    def build_file_dirs(self, dirs=['sites/default/files']):
        """ Creates files directory within the Drupal installation.
        dirs: List. Optional: list of file directories to create.
              Defaults to ['sites/default/files'].
              All paths are relative to Drupal installation.

        """
        for file_dir in dirs:
            path = os.path.join(self.working_dir, file_dir)
            local("mkdir -p %s " % path)
            with open('%s/.gitignore' % path, 'a') as f:
                f.write('*\n')
                f.write('!.gitignore\n')

    def build_settings_file(self, site='default'):
        """ Create settings.php and pantheon.settings.php
        Site: Optional. The drupal site name. Defaults to 'default'.

        """
        site_dir = os.path.join(self.working_dir, 'sites/%s/' % (site))
        local("cp %s %s" % (site_dir + 'default.settings.php', site_dir + 'settings.php'))
        pantheon.create_pantheon_settings_file(site_dir)

    def setup_database(self):
        """ Create a new database and set user grants (all).

        """
        for env in self.environments:
            project.BuildTools.setup_database(self, env, self.db_password)

    def setup_permissions(self):
        project.BuildTools.setup_permissions(self, handler='install')

    def setup_environments(self):
        project.BuildTools.setup_environments(self, tag='initialization')

    def push_to_repo(self):
        project.BuildTools.push_to_repo(tag='initialization')

    def cleanup(self):
        """ Remove working directory.

        """
        local('rm -rf %s' % self.working_dir)

