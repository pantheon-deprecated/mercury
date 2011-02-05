# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import random
import string
import tarfile
import tempfile
import time
import urllib2
import zipfile
import json
import re

import postback
import hudsontools

from fabric.api import *

ENVIRONMENTS = set(['dev','test','live'])
TEMPLATE_DIR = '/opt/pantheon/fab/templates'

def get_environments():
    """ Return list of development environments.

    """
    return ENVIRONMENTS

def get_template(template):
    """Return full path to template file.
    template: template file name

    """
    return os.path.join(get_template_dir(), template)

def get_template_dir():
    """Return template directory.

    """
    return TEMPLATE_DIR

def copy_template(template, destination):
    """Copy template to destination.
    template: template file name
    destination: full path to destination

    """
    local('cp %s %s' % (get_template(template),
                        destination))

def build_template(template_file, values):
    """Return a template object of the template_file with substitued values.
    template_file: full path to template file
    values: dictionary of values to be substituted in template file

    """
    contents = local('cat %s' % template_file)
    template = string.Template(contents)
    template = template.safe_substitute(values)
    return template

def is_aws_server():
    # Check if aws.server file was created during configure.
    return os.path.isfile('/etc/pantheon/aws.server')

def is_ebs_server():
    # Check if ebs.server file was created during configure.
    return os.path.isfile('/etc/pantheon/ebs.server')

def is_private_server():
    # Check if private.server file was created during configure.
    return os.path.isfile('/etc/pantheon/private.server')

def random_string(length):
    """ Create random string of ascii letters & digits.
    length: Int. Character length of string to return.

    """
    return ''.join(['%s' % random.choice (string.ascii_letters + \
                                          string.digits) \
                                          for i in range(length)])

def parse_vhost(path):
    """Helper method that returns environment variables from a vhost file.
    path: full path to vhost file.
    returns: dict of all vhost SetEnv variables.

    """
    env_vars = dict()
    with open(path, 'r') as f:
       vhost = f.readlines()
    for line in vhost:
        line = line.strip()
        if line.find('SetEnv') != -1:
            var = line.split()
            env_vars[var[1]] = var[2]
    return env_vars

def is_drupal_installed(project, environment):
    """Return True if the Drupal installation process has been completed.
       project: project name
       environment: environment name.

    """
    #TODO: Find better way of determining this than hitting the db.
    (username, password, db_name) = get_database_vars(project, environment)
    with hide('running'):
        status = local("mysql -u %s -p%s %s -e 'show tables;' | \
                        awk '/system/'" % (username, password, db_name))
    # If any data is in status, assume site is installed.
    return bool(status)

def download(url, prefix='tmp'):
    """Download url to temporary directory and return path to file.
    url: fully qualified url of file to download.
    prefix: optional prefix to use for the temporary directory name.
    returns: full path to downloaded file.

    """
    download_dir = tempfile.mkdtemp(prefix=prefix)
    filebase = os.path.basename(url)
    filename = os.path.join(download_dir, filebase)

    curl(url, filename)
    return filename

def curl(url, destination):
    """Use curl to save url to destination.
    url: url to download
    destination: full path/ filename to save curl output.

    """
    local('curl "%s" -o "%s"' % (url, destination))

def hudson_running():
    """Check if hudson is running. Returns True if http code == 200.

    """
    try:
        result = urllib2.urlopen('http://127.0.0.1:8090').code
    except:
        return False
    return result == 200

def hudson_queued():
    """Returns number of jobs Hudson currently has in its queue. -1 if unknown.

    """
    try:
        result = urllib2.urlopen('http://127.0.0.1:8090/queue/api/python')
    except:
        return -1
    if result.code != 200:
        return -1
    return len(eval(result.read()).get('items'))

def get_database_vars(project, environment):
    """Helper method that returns database variables for a project/environment.
    project: project name
    environment: environment name.
    returns: Tuple: (username, password, db_name)

    """
    vhost = PantheonServer().get_vhost_file(project, environment)
    env_vars = parse_vhost(vhost)
    return (env_vars.get('db_username'),
            env_vars.get('db_password'),
            env_vars.get('db_name'))

def configure_root_certificate(pki_server):
    """Helper function that connects to pki.getpantheon.com and configures the
    root certificate used throughout the infrastructure."""

    # Download and install the root CA.
    local('curl %s | sudo tee /usr/share/ca-certificates/pantheon.crt' % pki_server)
    local('echo "pantheon.crt" | sudo tee -a /etc/ca-certificates.conf')
    #local('cat /etc/ca-certificates.conf | sort | uniq | sudo tee /etc/ca-certificates.conf') # Remove duplicates.
    local('sudo update-ca-certificates')

def hudson_restart():
    local('curl -X POST http://localhost:8090/safeRestart')

def parse_drush_output(drush_output):
    """ Return drush backend json as a dictionary.
    drush_output: drush backend json output.
    """
    # Create the patern
    pattern = re.compile('DRUSH_BACKEND_OUTPUT_START>>>%s<<<DRUSH_BACKEND_OUTPUT_END' % '(.*)')

    # Match the patern, returning None if not found.
    match = pattern.match(drush_output)

    if match:
        return json.loads(match.group(1))

    return None

class PantheonServer:

    def __init__(self):
        # Ubuntu / Debian
        if os.path.exists('/etc/debian_version'):
            self.distro = 'ubuntu'
            self.mysql = 'mysql'
            self.owner = 'root'
            self.web_group = 'www-data'
            self.hudson_group = 'nogroup'
            self.tomcat_owner = 'tomcat6'
            self.tomcat_version = '6'
            self.webroot = '/var/www/'
            self.ftproot = '/srv/ftp/pantheon/'
            self.vhost_dir = '/etc/apache2/sites-available/'
        # Centos
        elif os.path.exists('/etc/redhat-release'):
            self.distro = 'centos'
            self.mysql = 'mysqld'
            self.owner = 'root'
            self.web_group = 'apache'
            self.hudson_group = 'hudson'
            self.tomcat_owner = 'tomcat'
            self.tomcat_version = '5'
            self.webroot = '/var/www/html/'
            self.ftproot = '/var/ftp/pantheon/'
            self.vhost_dir = '/etc/httpd/conf/vhosts/'
        #global
        self.template_dir = get_template_dir()

    def get_hostname(self):
        if os.path.exists("/usr/local/bin/ec2-metadata"):
            return local('/usr/local/bin/ec2-metadata -p | sed "s/public-hostname: //"').rstrip('\n')
        else:
            return local('hostname').rstrip('\n')

    def update_packages(self):
        if (self.distro == "centos"):
            local('yum clean all', capture=False)
            local('yum -y update', capture=False)
        else:
            local('apt-get -y update', capture=False)
            local('apt-get -y dist-upgrade', capture=False)

    def restart_services(self):
        if self.distro == 'ubuntu':
            local('/etc/init.d/apache2 restart')
            local('/etc/init.d/memcached restart')
            local('/etc/init.d/tomcat6 restart')
            local('/etc/init.d/varnish restart')
            local('/etc/init.d/mysql restart')
        elif self.distro == 'centos':
            local('/etc/init.d/httpd restart')
            local('/etc/init.d/memcached restart')
            local('/etc/init.d/tomcat5 restart')
            local('/etc/init.d/varnish restart')
            local('/etc/init.d/mysqld restart')

    def setup_iptables(self, file):
        local('/sbin/iptables-restore < ' + file)
        local('/sbin/iptables-save > /etc/iptables.rules')

    def create_drush_alias(self, drush_dict):
        """ Create an alias.drushrc.php file.
        drush_dict: project:
                    environment:
                    root: full path to drupal installation

        """
        alias_template = get_template('drush.alias.drushrc.php')
        alias_file = '/opt/drush/aliases/%s_%s.alias.drushrc.php' % (
                                            drush_dict.get('project'),
                                            drush_dict.get('environment'))
        template = build_template(alias_template, drush_dict)
        with open(alias_file, 'w') as f:
            f.write(template)

    def create_vhost(self, filename, vhost_dict, vhost_template_file = None):
        """
        filename:  vhost filename
        vhost_dict: server_name:
                    server_alias:
                    project:
                    environment:
                    db_name:
                    db_username:
                    db_password:
                    db_solr_path:
                    memcache_prefix:

        """
        if (vhost_template_file == None):
          vhost_template_file = 'vhost.template.%s' % self.distro
        vhost_template = get_template(vhost_template_file)
        template = build_template(vhost_template, vhost_dict)
        vhost = os.path.join(self.vhost_dir, filename)
        with open(vhost, 'w') as f:
            f.write(template)
        local('chown root:%s %s' % (self.web_group, vhost))
        local('chmod 640 %s' % vhost)

    def create_solr_index(self, project, environment, version):
        """ Create solr index in: /var/solr/project/environment.
        project: project name
        environment: development environment
        version: major drupal version

        """

        # Create project directory
        project_dir = '/var/solr/%s/' % project
        if not os.path.exists(project_dir):
            local('mkdir %s' % project_dir)
        local('chown %s:%s %s' % (self.tomcat_owner,
                                  self.tomcat_owner,
                                  project_dir))

        # Create data directory from sample solr data.
        data_dir = os.path.join(project_dir, environment)
        if os.path.exists(data_dir):
            local('rm -rf ' + data_dir)
        data_dir_template = os.path.join(get_template_dir(),
                                         'solr%s' % version)
        local('cp -R %s %s' % (data_dir_template, data_dir))
        local('chown -R %s:%s %s' % (self.tomcat_owner,
                                     self.tomcat_owner,
                                     data_dir))

        # Tell Tomcat where indexes are located.
        tomcat_template = get_template('tomcat_solr_home.xml')
        values = {'solr_path': '%s/%s' % (project, environment)}
        template = build_template(tomcat_template, values)
        tomcat_file = "/etc/tomcat%s/Catalina/localhost/%s_%s.xml" % (
                                                      self.tomcat_version,
                                                      project,
                                                      environment)
        with open(tomcat_file, 'w') as f:
            f.write(template)
        local('chown %s:%s %s' % (self.tomcat_owner,
                                  self.tomcat_owner,
                                  tomcat_file))


    def create_drupal_cron(self, project, environment):
        """ Create Hudson drupal cron job.
        project: project name
        environment: development environment

        """
        # Create job directory
        jobdir = '/var/lib/hudson/jobs/cron_%s_%s/' % (project, environment)
        if not os.path.exists(jobdir):
            local('mkdir -p ' + jobdir)

        # Create job from template
        values = {'drush_alias':'@%s_%s' % (project, environment)}
        cron_template = get_template('hudson.drupal.cron')
        template = build_template(cron_template, values)
        with open(jobdir + 'config.xml', 'w') as f:
            f.write(template)

        # Set Perms
        local('chown -R %s:%s %s' % ('hudson', self.hudson_group, jobdir))


    def get_vhost_file(self, project, environment):
        """Helper method that returns the full path to the vhost file for a
        particular project/environment.
        project: project name
        environment: environment name.

        """
        filename = '%s_%s' % (project, environment)
        if environment == 'live':
            filename = '000_' + filename
        if self.distro == 'ubuntu':
            return '/etc/apache2/sites-available/%s' % filename
        elif self.distro == 'centos':
            return '/etc/httpd/conf/vhosts/%s' % filename

    def get_ldap_group(self):
        """Helper method to pull the ldap group we authorize.
        Helpful in keeping filesystem permissions correct.

        /etc/pantheon/ldapgroup is written as part of the configure_ldap job.

        """
        with open('/etc/pantheon/ldapgroup', 'r') as f:
            return f.readline().rstrip("\n")

    def set_ldap_group(self, require_group):
        """Helper method to pull the ldap group we authorize.
        Helpful in keeping filesystem permissions correct.

        /etc/pantheon/ldapgroup is written as part of the configure_ldap job.

        """
        with open('/etc/pantheon/ldapgroup', 'w') as f:
            f.write('%s' % require_group)

class PantheonArchive(object):

    def __init__(self, path):
        self.path = path
        self.filetype = self._get_archive_type()
        self.archive = self._open_archive()

    def extract(self):
        """Extract a tar/tar.gz/zip archive into a temporary directory.

        """
        destination = tempfile.mkdtemp()
        self.archive.extractall(destination)
        return destination

    def close(self):
        """Close the archive file object.

        """
        self.archive.close()

    def _get_archive_type(self):
        """Return the generic type of archive (tar/zip).

        """
        if tarfile.is_tarfile(self.path):
            hudsontools.junit_pass('Tar found.','ArchiveType')
            return 'tar'
        elif zipfile.is_zipfile(self.path):
            hudsontools.junit_pass('Zip found.','ArchiveType')
            return 'zip'
        else:
            err = 'Error: Not a valid tar/zip archive.'
            hudsontools.junit_fail(err,'ArchiveType')
            postback.build_error(err)

    def _open_archive(self):
        """Return an opened archive file object.

        """
        if self.filetype == 'tar':
            return tarfile.open(self.path, 'r')
        elif self.filetype == 'zip':
            return zipfile.ZipFile(self.path, 'r')

