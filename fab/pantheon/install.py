import os
import random
import re
import string
import sys
import tempfile

from fabric.api import *

import drupaltools
import pantheon
import project

def _drush_download(modules, destination):
    """ Download list of modules using Drush.
    modules: list of module names.

    """
    #TODO: temporary until integrated in pantheon repo
    temp_dir = tempfile.mkdtemp()
    with cd(temp_dir):
        for module in modules:
             with settings(warn_only=True):
                 result = local('drush -by dl %s' % module)
             pantheon.log_drush_backend(result)
        local('mv * %s' % destination)
    local('rm -rf %s' % temp_dir)

class InstallTools(project.BuildTools):

    def __init__(self, project, **kw):
        """ Initialize generic installation object & helper functions. """
        super(InstallTools, self).__init__()
        self.working_dir = tempfile.mkdtemp()
        self.author = 'Jenkins User <jenkins@pantheon>'
        self.destination = os.path.join(self.server.webroot, self.project)
        self.version = kw.get('version', 6)

    def setup_working_dir(self):
        super(InstallTools, self).setup_working_dir(self.working_dir)

    def process_gitsource(self, url):
        self.setup_project_repo(url)
        self.setup_project_branch()
        self.setup_working_dir()
        self.version = int(drupaltools.get_drupal_version(self.working_dir)[:1])

    def process_makefile(self, url):
        # Get makefile and store in a temporary location
        tempdir = tempfile.mkdtemp()
        makefile = os.path.join(tempdir, 'install.make')
        local('curl %s > %s' % (url, makefile))

        with open(makefile, 'r') as f:
            contents = f.read()

        # Determine core version. Default to 6.
        version = re.search('\s*core\s*=\s*([67])\..*', contents)
        if version is not None:
            try:
                self.version = int(version.group(1))
            except IndexError:
                self.version = 6
        else:
            self.version = 6

        # Now that we know the version, setup a local repository.
        super(InstallTools, self).setup_project_repo()

        # Comment out any pre-defined "core" as we will replace with pressflow.
        with cd(tempdir):
            # core defined like project[drupal] =
            local(r"sed -i 's/^\(.*projects\[drupal\].*\)/;\1/' install.make")
            # core defined like project[] =
            local(r"sed -i 's/^\(.*projects\[\]\s*=\s*[\s\"]drupal[\s\"].*\)/;\1/' install.make")

        # Replace 'core' with pressflow
        with open(makefile, 'a') as f:
            f.write('\nprojects[pressflow][type] = "core"')
            f.write('\nprojects[pressflow][download][type] = git')
            f.write('\nprojects[pressflow][download][url] = ' + \
            'git://github.com/pantheon-systems/pantheon%s.git\n' % self.version)

        # Remove the working directory, drush doesn't like it to exist.
        local('rmdir %s' % self.working_dir)
        local('drush make %s %s' % (makefile, self.working_dir), capture=False)

        # Makefiles could use vc repos as sources, remove all metadata.
        with cd(self.working_dir):
            with settings(hide('warnings'), warn_only=True):
                local("find . -depth -name .git -exec rm -fr {} \;")
                local("find . -depth -name .bzr -exec rm -fr {} \;")
                local("find . -depth -name .svn -exec rm -fr {} \;")
                local("find . -depth -name CVS -exec rm -fr {} \;")

        # Create a project branch
        with cd(os.path.join('/var/git/projects', self.project)):
            local('git branch %s' % self.project)

        # Get the .git data for the project repo, and put in the working_dir
        tempdir = tempfile.mkdtemp()
        local('git clone /var/git/projects/%s -b %s %s' % (self.project,
                                                           self.project,
                                                           tempdir))
        local('mv %s %s' % (os.path.join(tempdir, '.git'), self.working_dir))
        local('rm -r %s' % tempdir)

        # Commit the result of the makefile.
        with cd(self.working_dir):
            local('git add .')
            local("git commit -am 'Build from makefile'")

    def setup_database(self):
        """ Create a new database and set user grants. """
        for env in self.environments:
            super(InstallTools, self).setup_database(env, self.db_password)

    def setup_pantheon_modules(self):
        """ Add required modules to project branch. """
        if self.version == 6:
            modules = ['apachesolr','memcache','varnish']
        if self.version == 7:
            modules = ['apachesolr-7.x-1.0-beta3', 'memcache-7.x-1.0-beta3']
        module_dir = os.path.join(self.working_dir, 'sites/all/modules')
        local('mkdir -p %s' % module_dir)
        _drush_download(modules, module_dir)

    def setup_pantheon_libraries(self):
        super(InstallTools, self).setup_pantheon_libraries(self.working_dir)

    def setup_files_dir(self):
        """ Creates Drupal files directory and sets gitignore for all sub-files

        """
        path = os.path.join(self.working_dir, 'sites/default/files')
        local("mkdir -p %s " % path)
        with open('%s/.gitignore' % path, 'a') as f:
            f.write('*\n')
            f.write('!.gitignore\n')

    def setup_settings_file(self):
        """ Create settings.php and pantheon.settings.php

        """
        site_dir = os.path.join(self.working_dir, 'sites/default')
        super(InstallTools, self).setup_settings_file(site_dir)

    def setup_permissions(self):
        super(InstallTools, self).setup_permissions(handler='install')

    def push_to_repo(self):
        super(InstallTools, self).push_to_repo(tag='initialization')

    def cleanup(self):
        """ Remove working directory.

        """
        local('rm -rf %s' % self.working_dir)

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

