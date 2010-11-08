import os
import sys
import tempfile

import pantheon

from fabric.api import *

class BuildTools(object):
    """ Generic Pantheon project installation helper functions.

    """

    def __init__(self, project):
        """ Initialize generic project installation object & helper functions.
        project: the name of the project to be built.

        """
        self.server = pantheon.PantheonServer()

        self.project = project
        self.environments = pantheon.get_environments()
        self.project_path = os.path.join(self.server.webroot, project)

    def setup_project_repo(self):
        project_repo = os.path.join('/var/git/projects', self.project)

        # Clear existing
        if os.path.exists(project_repo):
            local('rm -rf %s' % project_repo)

        # Get Pantheon core
        local('git clone git://gitorious.org/pantheon/6.git %s' % project_repo)

        with cd(project_repo):
            # Drupal Core
            local('git fetch git://gitorious.org/drupal/6.git master:drupal_core')
            # Repo config
            local('git config receive.denycurrentbranch ignore')
            local('git config core.sharedRepository group')
            # Group write.
            local('chmod -R g+w .')
        # post-receive-hook
        post_receive_hook = os.path.join(project_repo,
                                         '.git/hooks/post-receive')
        pantheon.copy_template('git.hook.post-receive', post_receive_hook)
        local('chmod +x %s' % post_receive_hook)

    def setup_project_branch(self, revision=None):
        project_repo = os.path.join('/var/git/projects', self.project)
        with cd(project_repo):
            if revision:
                local('git branch %s %s' % (self.project, revision))
            else:
                local('git branch %s' % self.project)


    def setup_working_dir(self, working_dir):
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              working_dir))


    def setup_database(self, environment, password, db_dump=None):
        username = self.project
        database = '%s_%s' % (self.project, environment)

        pantheon.create_database(database)
        pantheon.set_database_grants(database, username, password)
        if db_dump:
            pantheon.import_db_dump(db_dump, database)

    def setup_pantheon_libraries(self, working_dir):
        module_dir = os.path.join(working_dir, 'sites/all/modules')
        # SolrPhpClient
        with cd(os.path.join(module_dir, 'apachesolr')):
            local('wget http://solr-php-client.googlecode.com/files/SolrPhpClient.r22.2009-11-09.tgz')
            local('tar xzf SolrPhpClient.r22.2009-11-09.tgz')
            local('rm -f SolrPhpClient.r22.2009-11-09.tgz')

    def setup_settings_file(self, site_dir):
        """ Setup pantheon.settings.php and settings.php.
        site_dir: path to the site directory. E.g. /var/www/sites/default

        """
        settings_file = os.path.join(site_dir, 'settings.php')
        settings_default = os.path.join(site_dir, 'default.settings.php')
        settings_pantheon = os.path.join(site_dir, 'pantheon.settings.php')

        # Make sure default.settings.php exists.
        if not os.path.isfile(settings_default):
            pantheon.curl('http://gitorious.org/pantheon/6/blobs/raw/master/' + \
                       'sites/default/default.settings.php', settings_default)

        # Make sure settings.php exists.
        if not os.path.isfile(settings_file):
            local('cp %s %s' % (settings_default, settings_file))

        # Create pantheon.settings.php and include it from settings.php
        pantheon.copy_template('pantheon.settings.php', site_dir)
        with open(os.path.join(site_dir, 'settings.php'), 'a') as f:
            f.write('\n/* Added by Pantheon */\n')
            f.write("include 'pantheon.settings.php';\n")


    def setup_drush_alias(self):
        """ Create drush aliases for each environment in a project.

        """
        for env in self.environments:
            vhost = self.server.get_vhost_file(self.project, env)
            root = os.path.join(self.server.webroot, self.project, env)
            drush_dict = {'project': self.project,
                          'environment': env,
                          'vhost_path': vhost,
                          'root': root}
            self.server.create_drush_alias(drush_dict)

    def setup_solr_index(self):
        """ Create solr index for each environment in a project.

        """
        for env in self.environments:
            self.server.create_solr_index(self.project, env)

    def setup_vhost(self, db_password):
        """ Create vhost files for each environment in a project.

        """
        for env in self.environments:

            if pantheon.is_private_server():
                server_alias = '%s.*' % env
            else:
                server_alias = '%s.*.gotpantheon.com' % env

            vhost_dict = {'server_name': env,
                          'server_alias': server_alias,
                          'project': self.project,
                          'environment': env,
                          'db_name': '%s_%s' % (self.project, env),
                          'db_username':self.project,
                          'db_password':db_password,
                          'solr_path': '/%s_%s' % (self.project, env),
                          'memcache_prefix': '%s_%s' % (self.project, env)}

            filename = '%s_%s' % (self.project, env)
            if env == 'live':
                filename = '000_' + filename

            self.server.create_vhost(filename, vhost_dict)
            if self.server.distro == 'ubuntu':
               local('a2ensite %s' % filename)

    def setup_drupal_cron(self):
        """ Create drupal cron jobs in hudson for each development environment.

        """
        for env in self.environments:
            self.server.create_drupal_cron(self.project, env)

    def setup_environments(self, handler=None, working_dir=None):
        local('rm -rf %s' % (os.path.join(self.server.webroot, self.project)))

        if handler == 'import':
            tempdir = tempfile.mkdtemp()
            dump_file = pantheon.export_data(self.project, 'dev', tempdir)

        for env in self.environments:
            # Code
            destination = os.path.join(self.project_path, env)
            local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                                 self.project,
                                                                 destination))
            # On import setup environment data and files.
            if handler == 'import':
                # Data (already exists in 'dev')
                if env != 'dev':
                    pantheon.import_data(self.project, env, dump_file)

                # Files
                source = os.path.join(working_dir, 'sites/default/files')
                file_dir = os.path.join(self.project_path, env,
                                                'sites/default')
                local('rsync -av %s %s' % (source, file_dir))

        if handler == 'import':
            local('rm -rf %s' % tempdir)

    def push_to_repo(self, tag='initialization'):
        """ Commit changes in working directory and push to central repo.

        """
        with cd(self.working_dir):
            local('git checkout %s' % self.project)
            local('git add -A .')
            local("git commit --author=\"%s\" -m 'Initialize Project: %s'" % (
                                                   self.author, self.project))
            local('git tag %s.%s' % (self.project, tag))
            local('git push')
            local('git push --tags')

    def setup_permissions(self, handler, environment=None):
        """ Set permissions on project directory, settings.php, and files dir.

        """
        # Get  owner
        #TODO: Allow non-getpantheon users to set a default user.
        if os.path.exists("/etc/pantheon/ldapgroup"):
            owner = self.server.get_ldap_group()
        else:
            owner = self.server.web_group

        # During code updates, we only make changes in one environment.
        # Otherwise, in some cases we are modifying all environments.
        environments = list()
        if handler == 'update':
            #Single environment
            environments.append(environment)
        else:
            #All environments.
            environments = self.environments


        """
        Project directory and sub files/directories

        """

        # For new installs / imports / restores, use recursive chown.
        if handler in ['install', 'import', 'restore']:
            with cd(self.server.webroot):
                local('chown -R %s:%s %s' % (owner, owner, self.project))
                local('chmod -R g+w %s' % (self.project))

        # For code updates, be more specific (for performance reasons)
        elif handler == 'update':
            # Only make changes in the environment being updated.
            with cd(os.path.join(self.project_path,
                                 environments[0])):
                # Set ownership on everything exept files directory.
                #TODO: Restrict chown to files changed in git diff.
                local("find . \( -path ./sites/default/files -prune \) \
                       -o \( -exec chown %s:%s '{}' \; \)" % (owner, owner))


        """
        Files directory and sub files/directories

        """

        # For installs, just set 770 on files dir.
        if handler == 'install':
            for env in environments:
                site_dir = os.path.join(self.project_path,
                                        env,
                                        'sites/default')
                with cd(site_dir):
                    local('chmod 770 files')
                    local('chown %s:%s files' % (self.server.web_group,
                                                 self.server.web_group))

        # For imports or restores: 770 on files dir (and subdirs). 660 on files
        elif handler in ['import', 'restore']:
            for env in environments:
                file_dir = os.path.join(self.project_path, env,
                                        'sites/default/files')
                with cd(file_dir):
                    local("chmod 770 .")
                    # All sub-files
                    local("find . -type d -exec find '{}' -type f \; | \
                           while read FILE; do chmod 660 \"$FILE\"; done")
                    # All sub-directories
                    local("find . -type d -exec find '{}' -type d \; | \
                          while read DIR; do chmod 770 \"$DIR\"; done")
                    # Apache should own files/*
                    local("chown -R %s:%s ." % (self.server.web_group,
                                                self.server.web_group))

        # For updates, set apache as owner of files dir.
        elif handler == 'update':
            site_dir = os.path.join(self.project_path,
                                    environments[0],
                                    'sites/default')
            with cd(site_dir):
                local('chown %s:%s files' % (self.server.web_group,
                                             self.server.web_group))


        """
        settings.php & pantheon.settings.php

        """

        #TODO: We could split this up based on handler, but changing perms on
        # two files is fast. Ignoring for now, and treating all the same.
        for env in environments:
            if pantheon.is_drupal_installed(self.project, env):
                # Drupal installed, Apache does not need to own settings.php
                settings_perms = '440'
                settings_owner = owner
                settings_group = self.server.web_group
            else:
                # Drupal is NOT installed. Apache must own settings.php
                settings_perms = '660'
                settings_owner = self.server.web_group
                settings_group = self.server.web_group

            site_dir = os.path.join(self.project_path, env, 'sites/default')
            with cd(site_dir):
                # settings.php
                local('chmod %s settings.php' % settings_perms)
                local('chown %s:%s settings.php' % (settings_owner,
                                                    settings_group))
                # pantheon.settings.php
                local('chmod 440 pantheon.settings.php')
                local('chown %s:%s pantheon.settings.php' % (owner,
                                                             settings_group))


