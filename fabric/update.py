# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
import tempfile
import os

from pantheon import pantheon


def update_pantheon():
       print("Updating Pantheon from Launchpad")
       local('/etc/init.d/bcfg2-server stop')
       local('cd /opt/pantheon; bzr up')
       pantheon.restart_bcfg2()
       local('/usr/sbin/bcfg2 -vq', capture=False)
       print("Pantheon Updated")

def update_pressflow(project=None):
       server = pantheon.PantheonServer()
       temporary_directory = tempfile.mkdtemp()
       print ("Updating Pressflow")
       if (project == None):
              print("No project selected. Using 'projects'")
              project = 'projects'
       
       local('git clone /var/git' + project + ' ' + temporary_directory)
       with('cd temporary_directory'):
              local('got checkout -b testing')
              local('git pull git://gitorious.org/pantheon/6.git')
              local('git checkout master')
              local('git merge testing')
              local('git push /var/git' + project)

       local('rm -rf ' + temporary_directory)
       with cd('/var/git/' + project):
            local('git checkout master')
            local('git pull')
            #update all branches
            branches = local('git branch')
            for branch in branches:
                   temp = branch.lstrip('* ').rstrip('\n')
                   if (temp == "master"):
                          local('skipping master branch')
                   else:
                          local('git checkout temp')
                          local('git pull master')

       print("Pressflow Updated")

def update_data(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()
       source_temporary_directory = tempfile.mkdtemp()
       target_temporary_directory = tempfile.mkdtemp()

       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'live'")
              source_environment = 'live'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       source_location = server.webroot + source_project + '/' + source_environment + "/"
       target_location = server.webroot + target_project + '/' + target_environment + "/"

       print('Exporting ' + source_project + '/' + source_environment + ' database to temporary directory %s' % source_temporary_directory)
       sites = pantheon.export_data(source_location, source_temporary_directory)
       print('Exporting ' + target_project + '/' + target_environment + ' database to temporary directory %s' % target_temporary_directory)
       pantheon.export_data(target_location, target_temporary_directory)

       # NOTE: Name changes should be done outside the import function (no logic, just import).
       #       Added the below as a temporary stop-gap until the TODO is fixed.
       for site in sites:
           site.database.name = target_project + "_" + target_environment

       # TODO: update process needs to be multi-site friendly. Can't use project_environment (e.g. pantheon_dev) for database name.
       #       instead we should use project_environment_sitename (e.g. pantheon_dev_getpantheon_com for sites/getpantheon.com)
       #       this namespacing will allow multi-codebase & multi-site installs. Once supported, can use:
       #       project + "_" + environment + "_" + site.get_safe_name()

       pantheon.import_data(sites)
       print(target_project + '/' + target_environment + ' database updated with database from ' + source_project + '/' + source_environment)

def update_code(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()

       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'dev'")
              source_environment = 'dev'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       source_location = server.webroot + source_project + '/' + source_environment + "/"
       target_location = server.webroot + target_project + '/' + target_environment + "/"

       #commit any changes in source dir:
       if os.path.exists(source_location + '.git'):
              with cd(source_location):
                     with settings(warn_only=True):
                            local('git add -A .')
                            local('git commit -av -m "committing found changes"')
       else:
              abort("Source target not in version control.")

       #update target dir:
       if os.path.exists(target_location + '.git'):
              with cd(target_location):
                     local('git pull')
       else:
              abort("Source target not in version control.")

       update_permissions(source_location, server)
       update_permissions(target_location, server)
       print(target_project + '/' + target_environment + ' project updated from ' + source_project + '/' + source_environment)
       
def update_files(source_project=None, source_environment=None, target_project=None, target_environment=None):
       server = pantheon.PantheonServer()

       if (source_project == None):
              print("No source_project selected. Using 'pantheon'")
              source_project = 'pantheon'
       if (source_environment == None):
              print("No source_environment selected. Using 'live'")
              source_environment = 'live'
       if (target_project == None):
              print("No target_project selected. Using 'pantheon'")
              target_project = 'pantheon'
       if (target_environment == None):
              print("No target_environment selected. Using 'test'")
              target_environment = 'test'

       local('rsync -av --delete '+ server.webroot + source_project + '/' + source_environment + '/sites/all/files ' + server.webroot + target_project + '/' + target_environment + '/sites/all/')
       local('rsync -av --delete '+ server.webroot + source_project + '/' + source_environment + '/sites/default/files ' + server.webroot + target_project + '/' + target_environment + '/sites/default/')
       print(target_project + '/' + target_environment + ' files updated from ' + source_project + '/' + source_environment)

def update_permissions(dir, server):
       with cd(dir):
              local('chown -R root:' + server.web_group + ' *')
              local('chown ' + server.group + ':' + server.web_group + ' sites/default/settings.php')
              local('chmod 660 sites/default/settings.php')
              local('find . -type d -exec chmod 755 {} \;')
              local('find sites/*/files -type d -exec chmod 775 {} \;')
              local('find sites/*/files -type f -exec chmod 660 {} \;')

