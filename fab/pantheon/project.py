import os
import sys
import tempfile

import dbtools
import pantheon
import ygg

from fabric.api import *


class BuildTools(object):
    """ Generic Pantheon project installation helper functions.

    This is generally used as a base object, inherited by other project
    building classes (install, import, and restore). The child classes
    can use these methods directly or override/expand base processes.

    """
    def __init__(self):
        """ Initialize generic project installation object & helper functions.
        project: the name of the project to be built.

        """
        config = ygg.get_config()
        self.server = pantheon.PantheonServer()

        self.project = config.keys()[0]
        self.config = config[self.project]
        self.environments = set(self.config['environments'].keys())
        self.project_path = os.path.join(self.server.webroot, self.project)
        self.db_password = self.config\
                ['environments']['live']['mysql']['db_password']

    def bcfg2_project(self):
        local('bcfg2 -vqedb projects', capture=False)

    def remove_project(self):
        """ Remove a project and all related files/configs from the server.

        """
        locations = list()

        # Git repository
        locations.append(os.path.join('/var/git/projects', self.project))
        # Project webroot
        locations.append(self.project_path)

        # TODO: We also need to remove the following:
        # Solr Index
        # Apache vhost
        # Jenkins cron
        # Drush alias
        # Databases

        for location in locations:
            if os.path.exists(location):
                local('rm -rf %s' % location)

    def setup_project_repo(self):
        """ Create a new project repo, and download pantheon/drupal core.

        """
        project_repo = os.path.join('/var/git/projects', self.project)

        # Get Pantheon core
        local('git clone --mirror ' + \
              'git://git.getpantheon.com/pantheon/%s.git %s' % (self.version,
                                                                project_repo))

        with cd(project_repo):
            # Drupal Core
            #TODO: Use official Drupal git repo once available.
            local('git fetch git://git.getpantheon.com/drupal/' + \
                  '%s.git master:drupal_core' % (self.version))
            # Repo config
            local('git config core.sharedRepository group')
            # Group write.
            local('chmod -R g+w .')

        # post-receive-hook
        post_receive_hook = os.path.join(project_repo,
                                         'hooks/post-receive')
        pantheon.copy_template('git.hook.post-receive', post_receive_hook)
        local('chmod +x %s' % post_receive_hook)

    def setup_project_branch(self, revision=None):
        """ Create a branch of the project.
        revision: optional revision (hash/tag) at which to create the branch.

        """
        project_repo = os.path.join('/var/git/projects', self.project)
        with cd(project_repo):
            if revision:
                local('git branch %s %s' % (self.project, revision))
            else:
                local('git branch %s' % self.project)

    def setup_working_dir(self, working_dir):
        """ Clone a project to a working directory for processing.
        working_dir: temp directory for project processing (import/restore)

        """
        local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                              self.project,
                                                              working_dir))

    def setup_database(self, environment, password, db_dump=None, onramp=False):
        """ Create a new database based on project_environment, using password.
        environment: the environment name (dev/test/live) in which to create db
        password: password to identify user (username is same as project name).
        db_dump (optional): full path to database dump to import into db.
        onramp (optional): bool. perform additional prep during import process.

        """
        username = self.project
        database = '%s_%s' % (self.project, environment)

        dbtools.create_database(database)
        dbtools.set_database_grants(database, username, password)
        if db_dump:
            dbtools.import_db_dump(db_dump, database)
            if onramp:
                dbtools.clear_cache_tables(database)
                dbtools.convert_to_innodb(database)

    def setup_pantheon_libraries(self, working_dir):
        """ Download Pantheon required libraries.
        working_dir: full path to the temp processing directory.

        """
        module_dir = os.path.join(working_dir, 'sites/all/modules')
        # SolrPhpClient
        with cd(os.path.join(module_dir, 'apachesolr')):
            local('wget http://solr-php-client.googlecode.com/' + \
                  'files/SolrPhpClient.r22.2009-11-09.tgz')
            local('tar xzf SolrPhpClient.r22.2009-11-09.tgz')
            local('rm -f SolrPhpClient.r22.2009-11-09.tgz')

    def setup_settings_file(self, site_dir):
        """ Setup pantheon.settings.php and settings.php.
        site_dir: path to the site directory. E.g. /var/www/sites/default

        """
        settings_file = os.path.join(site_dir, 'settings.php')
        settings_default = os.path.join(site_dir, 'default.settings.php')
        settings_pantheon = os.path.join(site_dir, 'pantheon.settings.php')

        # Stomp on changes to default.settings.php - no need to conflict here.
        settings_contents = local(
           'git --git-dir=/var/git/projects/%s cat-file ' % self.project + \
           'blob refs/heads/master:sites/default/default.settings.php > %s' % (
                                                             settings_default))
        # Make sure settings.php exists.
        if not os.path.isfile(settings_file):
            local('cp %s %s' % (settings_default, settings_file))

        # Comment out $base_url entries.
        local("sed -i 's/^[^#|*]*\$base_url/# $base_url/' %s" % settings_file)

        # Create pantheon.settings.php and include it from settings.php
        ps_template = pantheon.get_template('pantheon%s.settings.php' % \
                                            self.version)
        ps_dict = {'project': self.project,
                   'vhost_root': self.server.vhost_dir}
        template = pantheon.build_template(ps_template, ps_dict)
        with open(settings_pantheon, 'w') as f:
            f.write(template)

        with open(os.path.join(site_dir, 'settings.php'), 'a') as f:
            f.write('\n/* Added by Pantheon */\n')
            f.write("include 'pantheon.settings.php';\n")

    def setup_drush_alias(self):
        """ Create drush aliases for each environment in a project.

        """
        for env in self.environments:
            root = os.path.join(self.server.webroot, self.project, env)
            drush_dict = {'project': self.project,
                          'environment': env,
                          'root': root}
            self.server.create_drush_alias(drush_dict)

    def setup_solr_index(self):
        """ Create solr index for each environment in a project.

        """
        for env in self.environments:
            self.server.create_solr_index(self.project, env, self.version)

    def setup_drupal_cron(self):
        """ Create drupal cron jobs in jenkins for each environment.

        """
        for env in self.environments:
            self.server.create_drupal_cron(self.project, env)

    def setup_environments(self, handler=None, working_dir=None):
        """ Send code/data/files from processing to destination (dev/test/live)
        All import and restore processing is done in temp directories. Once
        processing is complete, it is pushed out to the final destination.

        handler: 'import' or None. If import, complete extra import processing.
        working_dir: If handler is import, also needs full path to working_dir.

        """

        # During import, only run updates/import processes a single database.
        # Once complete, we import this 'final' database into each environment.
        if handler == 'import':
            tempdir = tempfile.mkdtemp()
            dump_file = dbtools.export_data(self, 'dev', tempdir)

        for env in self.environments:
            # Code
            destination = os.path.join(self.project_path, env)
            local('git clone -l /var/git/projects/%s -b %s %s' % (self.project,
                                                                 self.project,
                                                                 destination))
            # On import setup environment data and files.
            if handler == 'import':
                # Data (already exists in 'dev' - import into other envs)
                if env != 'dev':
                    dbtools.import_data(self.project, env, dump_file)

                # Files
                source = os.path.join(working_dir, 'sites/default/files')
                file_dir = os.path.join(self.project_path, env,
                                                'sites/default')
                local('rsync -av %s %s' % (source, file_dir))

        # Cleanup
        if handler == 'import':
            local('rm -rf %s' % tempdir)

    def push_to_repo(self, tag):
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

        handler: one of: 'import','restore','update','install'. How the
        permissions are set is determined by the handler.

        environment: In most cases this is left to None, as we will be
        processing all environments using self.environments. However,
        if handler='update' we need to know the specific environment for which
        the update is being run. We do this so we are not forcing permissions
        updates on files that have not changed.

        """
        # Get  owner
        #TODO: Allow non-getpantheon users to set a default user.
        if os.path.exists("/etc/pantheon/ldapgroup"):
            owner = self.server.get_ldap_group()
        else:
            owner = self.server.web_group

        # During code updates, we only make changes in one environment.
        # Otherwise, we are modifying all environments.
        environments = list()
        if handler == 'update':
            #Single environment during update.
            environments.append(environment)
        else:
            #All environments for install/import/restore.
            environments = self.environments


        """
        Project directory and sub files/directories

        """

        # installs / imports / restores.
        if handler in ['install', 'import', 'restore']:
            # setup shared repo config and set gid
            for env in environments:
                with cd(os.path.join(self.server.webroot, self.project, env)):
                    local('git config core.sharedRepository group')
            with cd(self.server.webroot):
                local('chown -R %s:%s %s' % (owner, owner, self.project))


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
            if pantheon.is_drupal_installed(self, env):
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

