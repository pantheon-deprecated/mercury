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
import rangeable_file
from vars import *

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

    def free_space(self):
        """Returns bool. True if free space is greater then backup size.

        """
        #Get the total free space
        fs = os.statvfs('/')
        fs = int(fs.f_bavail * fs.f_frsize / 1024)
        #Calc the disk usage of project webroot and git repo
        paths = [os.path.join(self.server.webroot, self.project),
                 os.path.join('/var/git/projects', self.project)]
        result = local('du -slc {0}'.format(' '.join(paths)))
        ns = int(result[result.rfind('\n')+1:result.rfind('\t')])
        #Calc the database size of each env
        for env in self.environments:
            result = local('mysql --execute=\'SELECT IFNULL(ROUND((' \
                'sum(DATA_LENGTH) + sum(INDEX_LENGTH) - sum(DATA_FREE))' \
                '/1024), 0) AS Size FROM INFORMATION_SCHEMA.TABLES where ' \
                'TABLE_SCHEMA =  "{0}_{1}"\G\''.format(self.project, env))
            ns += int(result[result.rfind(' ')+1:])
        #Double needed space to account for tarball
        return fs > (ns*2)

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

    def move_archive(self):
        """Move archive from temporary working dir to S3.

        """
        self.log.info('Moving archive to external storage.')
        path = '%s/%s' % (self.working_dir, self.name)
        try:
            Archive(path).submit()
        except:
            self.log.exception('Upload to remote storage unsuccessful.')
        else:
            self.log.info('Upload %s to remote storage complete.' % self.name)

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

class Archive():
    def __init__(self, path, threshold=4194304000, chunk_size=4194304000):
        """Initiates an archivable file object

        Keyword arguements:
        path       -- the path to the file
        threshold  -- filesize at which we switch to multipart upload
        chunk_size -- the size to break multipart uploads into

        """
        self.connection = httplib.HTTPSConnection(
                                                  API_HOST,
                                                  API_PORT,
                                                  key_file = VM_CERTIFICATE,
                                                  cert_file = VM_CERTIFICATE)
        self.path = path
        self.filesize = os.path.getsize(path)
        self.threshold = threshold
        self.filename = os.path.basename(path)
        self.partno = 0
        self.parts = []
        self.chunk_size = chunk_size
        self.log = logger.logging.getLogger('pantheon.backup.Archive')

    def is_multipart(self):
        # Amazon S3 has a minimum upload size of 5242880
        assert self.filesize >= 5242880,"File size is too small."
        assert self.chunk_size >= 5242880,"Chunk size is too small."
        return True if self.filesize > self.threshold else False

    def submit(self):
        if self.filesize < self.threshold:
            # Amazon S3 has a maximum upload size of 5242880000
            assert self.threshold < 5242880000,"Threshold is too large."
            fo = open(self.path)
            info = json.loads(self._get_upload_header(fo))
            response = self._arch_request(fo, info)
            self._complete_upload()
        elif self.is_multipart():
            self.log.info('Large backup detected. Using multipart upload ' \
                          'method.')
            #TODO: Use boto to get upid after next release
            #self.upid = json.loads(self._initiate_multipart_upload())
            info = json.loads(self._initiate_multipart_upload())
            response = self._arch_request(None, info)
            from xml.etree import ElementTree
            self.upid = ElementTree.XML(response.read()).getchildren()[2].text
            for chunk in rangeable_file.fbuffer(self.path, self.chunk_size):
                info = json.loads(self._get_multipart_upload_header(chunk))
                self.log.info('Sending part {0}'.format(self.partno))
                response = self._arch_request(chunk, info)
                etag = response.getheader('etag')
                self.parts.append((self.partno, etag))
            self._complete_multipart_upload()
        self.connection.close()

    def _hash_file(self, fo):
        """ Return MD5 hash of file object

        Keyword arguements:
        fo -- the file object to hash

        """
        fo_hash = hashlib.md5()
        for chunk in iter(lambda: fo.read(128*fo_hash.block_size), ''):
            fo_hash.update(chunk)
        return base64.b64encode(fo_hash.digest())

    def _initiate_multipart_upload(self):
        """ Return the upload id from api."""
        # Get the authorization headers.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'initiate'}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _get_multipart_upload_header(self, part):
        """ Return multipart upload headers from api.

        Keyword arguements:
        part -- file object to get headers for

        """
        # Get the MD5 hash of the file.
        self.log.debug("Archiving file at path: %s" % self.path)
        part_hash = self._hash_file(part)
        self.log.debug("Hash of file is: %s" % part_hash)
        self.partno+=1
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash,
                   'multipart': 'upload',
                   'upload-id': self.upid,
                   'part-number': self.partno}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _get_upload_header(self, fo):
        """ Return upload headers from api.

        Keyword arguements:
        fo -- file object to get headers for

        """
        self.log.debug("Archiving file at path: %s" % self.path)
        part_hash = self._hash_file(fo)
        self.log.debug("Hash of file is: %s" % part_hash)
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    #TODO: re-work multipart upload completion into the rest api
    def _complete_multipart_upload(self):
        """ Return multipart upload completion response from api."""
        # Notify the event system of the completed transfer.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'complete',
                   'upload-id': self.upid,
                   'parts': self.parts}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def _complete_upload(self):
        """ Return upload completion response from api."""
        path = "/sites/self/archive/{0}/complete".format(self.filename)
        return self._api_request(path)

    #TODO: Maybe refactored into the ygg library
    def _api_request(self, path, encoded_headers=None):
        """Returns encoded response data from api.

        Keyword arguements:
        path            -- api request path
        encoded_headers -- api request headers
        Make PUT request to config server.

        """
        self.connection.connect()
        if encoded_headers:
            self.connection.request("PUT", path, encoded_headers)
        else:
            self.connection.request("PUT", path)

        complete_response = self.connection.getresponse()
        if complete_response.status == 200:
            self.log.debug('Successfully obtained authorization.')
        else:
            self.log.error('Obtaining authorization failed.')
            raise Exception(complete_response.reason)
        encoded_info = complete_response.read()
        return encoded_info

    def _arch_request(self, data, info):
        """Returns encoded response data from archive server.

        Keyword arguements:
        data -- data to archive
        info -- api request headers
        Make PUT request to store data on archive server.

        """
        # Transfer the file to long-term storage.
        arch_connection = httplib.HTTPSConnection(info['hostname'])
        if data:
            data.seek(0,2)
            self.log.info('Sending %s bytes to remote storage' % data.tell())
            data.seek(0)
        arch_connection.request(info['verb'],
                                info['path'],
                                data,
                                info['headers'])
        arch_complete_response = arch_connection.getresponse()
        if arch_complete_response.status == 200:
            if data:
                self.log.info('Successfully pushed the file to remote storage.')
        else:
            self.log.error('Uploading file to remote storage failed.')
            raise Exception(arch_complete_response.reason)
        return arch_complete_response

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
