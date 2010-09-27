import os
import random
import string
import sys
import tempfile

from fabric.api import *

import pantheon


def _drush_download(modules):
    """ Download list of modules using Drush.
    modules: list of module names.

    """
    #TODO: temporary until integrated in pantheon repo
    for module in modules:
         local('drush -y dl %s' % module)


class InstallTools:
    """ Generic Drupal installation helper functions.
    
    """

    def __init__(self, project):
        """ Initialize generic installation object & helper functions.
        project: the name of the project to be built.

        """
        self.server = pantheon.PantheonServer()

        self.project = project
        self.db_password = pantheon.random_string(10)
        self.working_dir = tempfile.mkdtemp()
        self.destination = os.path.join(self.server.webroot, project)


    def build_project_branch(self):
        """ Bring master up to date and create a new project branch.

        """
        with cd('/var/git/projects'):
            local('git checkout master')
            local('git pull')
            with settings(hide('warnings'), warn_only=True):
                local('git tag -d %s.initialization' % self.project)
                local('git branch -D %s' % self.project)
            local('git branch %s' % self.project)


    def build_working_dir(self):
        """ Clone project to a temporary working directory.

        """
        local('git clone -l /var/git/projects -b %s %s' % (self.project, 
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
            local("git commit -m 'Add required modules'")


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
           local("git commit -m 'Add required libraries'")


    def build_makefile(self, makefile, flags=list()):
        """ Setup Drupal site using drush make
        makefile: full path to drush makefile
        flags: List. Optional: options to use with drush make.

        """
        opts = ''
        if flags:
            opts = ' '.join(['%s' % flag for flag in flags])
        local('rm -rf %s' % self.working_dir)
        local("drush make %s %s %s" % (opts, makefile, self.working_dir))


    def build_file_dirs(self, dirs=['sites/default/files']):
        """ Creates files directory within the Drupal installation.
        dirs: List. Optional: list of file directories to create.
              Defaults to ['sites/default/files'].
              All paths are relative to Drupal installation.

        """
        for file_dir in dirs:
            local("mkdir -p %s " % (os.path.join(self.working_dir, file_dir)))
            local("touch %s/.gitignore " % (os.path.join(self.working_dir, file_dir)))


    def build_gitignore(self, items=['sites/default/files/*',
                                     '!.gitignore']):
        """ Creates .gitignore entries.
        items: List. Optional: entries for .gitignore
              See function for default items.
              All paths are relative to Drupal installation.

        """
        with open(os.path.join(self.working_dir, '.gitignore'), 'w') as f:
            for item in items:
                f.write(item + '\n')


    def build_settings_file(self, site='default'):
        """ Create settings.php and pantheon.settings.php
        Site: Optional. The drupal site name. Defaults to 'default'.

        """
        site_dir = os.path.join(self.working_dir, 'sites/%s/' % (site))
        local("cp %s %s" % (site_dir + 'default.settings.php', site_dir + 'settings.php'))
        pantheon.create_pantheon_settings_file(site_dir)


    def build_database(self, environments=pantheon.get_environments()):
        """ Create a new database and set user grants (all).

        """
        username = self.project
        password = self.db_password

        for env in environments:      
            database = '%s_%s' % (self.project, env)
            local("mysql -u root -e 'DROP DATABASE IF EXISTS %s'" % (database))
            local("mysql -u root -e 'CREATE DATABASE IF NOT EXISTS %s'" % (database))
            local("mysql -u root -e \"GRANT ALL ON %s.* TO '%s'@'localhost' \
                                      IDENTIFIED BY '%s';\"" % (database,
                                                                username, 
                                                                password))


    def build_drush_alias(self, environments=pantheon.get_environments()):
        """ Create drush aliases for each environment in a project.
        environments: Optional. List.

        """
        for env in environments:
            vhost = self.server.get_vhost_file(self.project, env)
            root = os.path.join(self.server.webroot, self.project, env)
            drush_dict = {'project': self.project,
                          'environment': env,
                          'vhost_path': vhost,
                          'root': root}
            self.server.create_drush_alias(drush_dict)


    def build_solr_index(self, environments=pantheon.get_environments()):
        """ Create solr index for each environment in a project.
        environments: Optional. List.

        """
        for env in environments:
            self.server.create_solr_index(self.project, env)


    def build_vhost(self, environments=pantheon.get_environments()):
        """ Create vhost files for each environment in a project.
        environments: Optional. List. 

        """
        for env in environments:

            vhost_dict = {'project': self.project,
                          'environment': env,
                          'db_name': '%s_%s' % (self.project, env),
                          'db_username':self.project,
                          'db_password':self.db_password,
                          'solr_path': '/%s_%s' % (self.project, env),
                          'memcache_prefix': '%s_%s' % (self.project, env)}

            filename = '%s_%s' % (self.project, env)
            if env == 'live': 
                filename = '000_' + filename

            self.server.create_vhost(filename, vhost_dict)
            if self.server.distro == 'ubuntu':
               local('a2ensite %s' % filename)


    def build_drupal_cron(self, environments=pantheon.get_environments()):
        """ Create drupal cron jobs in hudson for each development environment.
        environments: Optional. List.

        """
        for env in environments:
            self.server.create_drupal_cron(self.project, env)


    def build_environments(self, tag='initialization', environments=pantheon.get_environments()):
       """ Clone project from central repo to all environments.
           environments: Optional. List.

       """ 
       local('rm -rf %s' % (os.path.join(self.server.webroot, self.project)))
       for env in environments:
           destination = os.path.join(self.server.webroot, self.project, env)
           local('git clone -l /var/git/projects -b %s %s' % (self.project, 
                                                              destination))

           with cd(destination):
               if env == 'dev':
                   local('git checkout master')
                   local('git checkout %s' % self.project)
               else:
                   local('git fetch')
                   local('git reset --hard %s.%s' % (self.project, tag))
                

    def build_permissions(self, environments=pantheon.get_environments()):
        """ Set permissions on project directory, settings.php, and files dir.
        environments: Optional. List.

        """
        with cd(self.server.webroot):
            local('chown -R root:%s %s' % (self.server.web_group, self.project))

        for env in environments:
            site_dir = os.path.join(self.server.webroot, \
                                    '%s/%s/sites/default' % (self.project, env))
            with cd(site_dir):
                local('chown %s:%s settings.php' % (self.server.web_group, 
                                                    self.server.web_group))
                local('chmod 660 settings.php')
                local('chmod 440 pantheon.settings.php')
                local('chmod 770 files')
        
    def build_ldap_client(self, base_domain = "example.com", require_group = None, server_host = "auth.example.com"):
        """ Set permissions on project directory, settings.php, and files dir.
        environments: Optional. List.
        
        """
        if server_host == "auth.example.com":
            server_host = "auth." + base_domain

        # If necessary, restrict by group
        if require_group is not None:
            #local("sudo echo '-:ALL EXCEPT root sudo (" + require_group + "):ALL' | tee -a /etc/security/access.conf")
            local("sudo echo 'AllowGroups root sudo " + require_group + "' | tee -a /etc/ssh/sshd_config")
        else:
            local("sudo echo 'AllowGroups root sudo' | tee -a /etc/ssh/sshd_config")

        local("sudo /etc/init.d/ssh restart")
            
        ldap_domain = _fabuntu_ldap_domain_to_ldap(base_domain)
            
        local("sudo apt-get install -y debconf-utils")
            
        ldap_auth_conf_template = loader.load('ldap-auth-config.preseed.cfg', cls=TextTemplate)
        ldap_auth_conf = ldap_auth_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
        with NamedTemporaryFile() as temp_file:
            temp_file.write(ldap_auth_conf)
            temp_file.seek(0)
            local("sudo debconf-set-selections " + temp_file.name)
        
        local("sudo apt-get install -y libnss-ldap ldap-auth-config")
        
        ldap_conf_template = loader.load('ldap.conf', cls=TextTemplate)
        ldap_conf = ldap_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
        with NamedTemporaryFile() as temp_file:
            temp_file.write(ldap_conf)
            temp_file.seek(0)
            local("sudo cp " + temp_file.name + " /etc/ldap.conf")

        local("sudo auth-client-config -t nss -p lac_ldap")
        

    def push_to_repo(self, tag='initialization'):
        """ Commit changes in working directory and push to central repo.

        """
        with cd(self.working_dir):
            local('git checkout %s' % self.project)
            local('git add -A .')
            local("git commit -m 'Initialize Project: %s'" % self.project)
            local('git tag %s.%s' % (self.project, tag))
            local('git push')
            local('git push --tags')\


    def cleanup(self):
        """ Remove working directory.

        """
        local('rm -rf %s' % self.working_dir)

