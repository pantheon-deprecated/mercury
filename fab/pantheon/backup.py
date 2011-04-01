import base64
import hashlib
import httplib
import json
import os
import string
import sys
import tempfile

from configobj import ConfigObj
from fabric.api import *

import pantheon
import logger
import ygg

CERTIFICATE = "/etc/pantheon/system.pem"
API_SERVER = "api.getpantheon.com"
ARCHIVE_SERVER = "s3.amazonaws.com"

def remove(archive):
    """Remove a backup tarball from the server.
    archive: name of the archive to remove.

    """
    log = logger.logging.getLogger('pantheon.backup.remove')
    try:
        server = pantheon.PantheonServer()
        path = os.path.join(server.ftproot, archive)
        if os.path.exists(path):
            local('rm -f %s' % path)
    except:
        log.exception('Removal of local backup archive was unsuccessful.')
        raise
    else:
        log.debug('Removal of local backup archive successful.')

class PantheonBackup():

    def __init__(self, name, project):
        """Initialize Backup Object.
        name: name of backup (resulting file: name.tar.gz)
        project: name of project to backup.

        """
        self.server = pantheon.PantheonServer()
        self.project =  project
        self.environments = pantheon.get_environments()
        self.working_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.working_dir, self.project)
        self.name = name + '.tar.gz'
        self.log = logger.logging.getLogger('pantheon.backup.PantheonBackup')
        self.log = logger.logging.LoggerAdapter(self.log, 
                                                {"project": project})

    def get_dev_code(self, user):
        """USED FOR REMOTE DEV: Clone of dev git repo.

        """
        self.log.info('Initialized archive of code.')
        try:
            server_name = _get_server_name(self.project)
            local('mkdir -p %s' % self.backup_dir)
            source = os.path.join(self.server.webroot, self.project, 'dev')
            destination = 'code'
            with cd(self.backup_dir):
                local('git clone %s -b %s %s' % (source,
                                                 self.project,
                                                 destination))
                # Manually set origin URL so remote pushes have a destination.
                with cd(destination):
                    local("sed -i 's/^.*url =.*$/\\turl = " + \
                    "%s@%s.gotpantheon.com:\/var\/git\/projects\/%s/' " \
                    ".git/config" % (user, server_name, self.project))
        except:
            self.log.exception('Archival of code was unsuccessful.')
            raise
        else:
            self.log.info('Archive of code successful.')

    def get_dev_files(self):
        """USED FOR REMOTE DEV: dev site files.

        """
        self.log.info('Initialized archive of files.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            source = os.path.join(self.server.webroot, self.project,
                                          'dev/sites/default/files')
            destination = self.backup_dir
            # If 'dev_code' exists in backup_dir, 
            # this is a full dev-archive dump.
            # Place the files within the drupal site tree.
            if os.path.exists(os.path.join(self.backup_dir, 
                                           'dev_code/sites/default')):
                destination = os.path.join(self.backup_dir, 
                                           'dev_code/sites/default')
            local('rsync -avz %s %s' % (source, destination))
        except:
            self.log.exception('Archival of files was unsuccessful.')
            raise
        else:
            self.log.info('Archive of files successful.')

    def get_dev_data(self):
        """USED FOR REMOTE DEV: dev site data.

        """
        self.log.info('Initialized archive of data.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                                     self.project, 'dev'))
            destination = os.path.join(self.backup_dir, 'dev_database.sql')
            self._dump_data(destination, drupal_vars)
        except:
            self.log.exception('Archival of data was unsuccessful.')
            raise
        else:
            self.log.info('Archive of data successful.')


    def get_dev_drushrc(self, user):
        """USED FROM REMOTE DEV: create a drushrc file.

        """
        self.log.info('Initialized archive of drush.')
        try:
            server_name = _get_server_name(self.project)
            local('mkdir -p %s' % self.backup_dir)
            # Build the environment specific aliases
            env_aliases = ''
            template = string.Template(_get_env_alias())

            for env in self.environments:
                values = {'host': '%s.gotpantheon.com' % server_name,
                          'user': user,
                          'project': self.project,
                          'env': env,
                          'root': '/var/www/%s/%s' % (self.project, env)}
                env_aliases += template.safe_substitute(values)

            destination = os.path.join(self.backup_dir,
                                       '%s.aliases.drushrc.php' % self.project)

            with open(destination, 'w') as f:
                f.write('<?php\n%s\n' % env_aliases)
        except:
            self.log.exception('Archival of drush was unsuccessful.')
            raise
        else:
            self.log.info('Archive of drush successful.')

    def backup_files(self):
        """Backup all files for environments of a project.

        """
        self.log.info('Initialized backup of files.')
        try:
            local('mkdir -p %s' % self.backup_dir)
            for env in self.environments:
                source = os.path.join(self.server.webroot, self.project, env)
                local('rsync -avz %s %s' % (source, self.backup_dir))
        except:
            self.log.exception('Backing up the files was unsuccessful.')
            raise
        else:
            self.log.info('Backup of files successful.')

    def backup_data(self):
        """Backup databases for environments of a project.

        """
        self.log.info('Initialized backup of data.')
        try:
            for env in self.environments:
                drupal_vars = pantheon.parse_vhost(self.server.get_vhost_file(
                                                   self.project, env))
                dest = os.path.join(self.backup_dir, env, 'database.sql')
                self._dump_data(dest, drupal_vars)
        except:
            self.log.exception('Backing up the data was unsuccessful.')
            raise
        else:
            self.log.info('Backup of data successful.')

    def backup_repo(self):
        """Backup central repository for a project.

        """
        self.log.info('Initialized backup of repo.')
        try:
            dest = os.path.join(self.backup_dir, '%s.git' % (self.project))
            local('rsync -avz /var/git/projects/%s/ %s' % (self.project, dest))
        except:
            self.log.exception('Backing up the repo was unsuccessful.')
            raise
        else:
            self.log.info('Backup of repo successful.')

    def backup_config(self, version):
        """Write the backup config file.
        version: int. Backup schema version. Used to maintain backward
                 compatibility as backup formats could change.

        """
        self.log.info('Initialized backup of config.')
        try:
            config_file = os.path.join(self.backup_dir, 'pantheon.backup')
            config = ConfigObj(config_file)
            config['backup_version'] = version
            config['project'] = self.project
            config.write()
        except:
            self.log.exception('Backing up the config was unsuccessful.')
            raise
        else:
            self.log.info('Backup of config successful.')

    def finalize(self, destination=None):
        """ Create archive, move to destination, remove working dir.

        """
        try:
            self.make_archive()
            self.move_archive()
        except:
            self.log.error('Failure creating/storing backup.')
        
        self.cleanup()

    def make_archive(self):
        """Tar/gzip the files to be backed up.

        """
        self.log.info('Making archive.')
        try:
            with cd(self.working_dir):
                local('tar czf %s %s' % (self.name, self.project))
        except:
            self.log.exception('Making of the archive was unsuccessful.')
            raise
        else:
            self.log.info('Make archive successful.')

    def move_archive(self, destination=None):
        """Move archive from temporary working dir to S3.

        """
        # TODO: maybe generalize this?
        self.log.info('Moving archive to external storage.')
        connection = getYggConnection()
        path = '%s/%s' % (self.working_dir, self.name)
        hash = hash_file(path)
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': hash}
        encoded_headers = json.dumps(headers)
        connection.request("PUT", "/sites/self/archive/" + self.name, encoded_headers)
        complete_response = connection.getresponse()
        if complete_response.status == 200:
            self.log.info('Successfully obtained authorization.')
        else:
            self.log.exception('Obtaining authorization failed.')
            
        encoded_info = complete_response.read()
        info = json.loads(encoded_info)

        # Transfer the file to long-term storage.
        file = open(path)
        st = os.stat(path)
        arch_connection = httplib.HTTPSConnection(info['hostname'])
        self.log.info('Sending %s bytes to remote storage' % st.st_size)
        arch_connection.request("PUT", info['path'], file, info['headers'])
        arch_complete_response = arch_connection.getresponse()
        if arch_complete_response.status == 200:
            # We get a fresh connection because who knows how long it took to 
            # transfer things to long-term storage
            connection = getYggConnection()
            connection.request("PUT", "/sites/self/archive/" + self.name + "/complete")
            try:
                yggresp = connection.getresponse()
                self.log.debug('Ygg complet notification status: %s' % yggresp.status)
                self.log.info('Upload %s to remote storage complete.' % self.name)
            except Exception as e:
                self.log.info('Error logging completion: %s' % e)
        else:
            self.log.exception('Uploading to remote storage.')
            

    def cleanup(self):
        """ Remove working_dir """
        self.log.debug('Cleaning up.')
        try:
            local('rm -rf %s' % self.working_dir)
        except:
            self.log.exception('Cleanup unsuccessful.')
            raise
        else:
            self.log.debug('Cleanup successful.')


    def _dump_data(self, destination, db_dict):
        """Dump a database to a .sql file.
        destination: Full path to dump file.
        db_dict: db_username
                 db_password
                 db_name

        """
        result = local("mysqldump --single-transaction \
                                  --user='%s' --password='%s' %s > %s" % (
                                         db_dict.get('db_username'),
                                         db_dict.get('db_password'),
                                         db_dict.get('db_name'),
                                         destination))
        if result.failed:
            abort("Export of database '%s' failed." % db_dict.get('db_name'))

def _get_server_name(project):
    """Return server name from apache alias "env.server_name.gotpantheon.com"
    """
    config = ygg.get_config()
    alias = config[project]['environments']['dev']['apache']['ServerAlias']
    return alias.split('.')[1]

def _get_env_alias():
    """Return slug of php for drushrc.

    """
    return """
$aliases['${project}_${env}'] = array(
  'remote-host' => '${host}',
  'remote-user' => '${user}',
  'uri' => 'default',
  'root' => '${root}',
);
"""

def hash_file(path):
    hash = hashlib.md5()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(128*hash.block_size), ''):
            hash.update(chunk)
    return base64.b64encode(hash.digest())

def getYggConnection():
    return httplib.HTTPSConnection(
        API_SERVER,
        8443,
        key_file = CERTIFICATE,
        cert_file = CERTIFICATE
    )