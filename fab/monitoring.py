# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import pdb
import smtplib
import socket
import urllib
import logging
import json
from pantheon import configrepo

from fabric.api import *

LOG_FILENAME = '/var/log/site_health'
FORMAT = '%(asctime)s [%(levelname)s] %(funcName)s: %(message)s'
DATEFORMAT='%a, %d %b %Y %H:%M:%S'
logging.basicConfig(level = logging.DEBUG,
                    filename = LOG_FILENAME,
                    format = FORMAT,
                    datefmt = DATEFORMAT)
logger = logging.getLogger('health')

def service_request(service='', method = "GET", status = None):
    if status is not None:
        status = json.dumps(status)
    url='https://api.getpantheon.com:8443/sites/self/services/%s' % service
    configrepo.request(method, status, url)

def check_load_average(limit):
    loads = os.getloadavg()
    if (float(loads[0]) > float(limit)):
        logger.warning('Load average is %s which is above the threshold of ' \
                       '%s.' % (str(loads[0]), str(limit)))
        status = {'status': 'WARN'}
    else:
        logger.info('Load average is %s which is below the threshold of %s.' % 
                    (str(loads[0]), str(limit)))
        status = {'status': 'OK'}
    service_request('load_average', 'PUT', status)

def check_disk_space(filesystem, limit):
    s = os.statvfs(filesystem)
    usage = (s.f_blocks - s.f_bavail)/float(s.f_blocks) * 100
    if (float(usage) > float(limit)):
        logger.warning('Disk usage of %s is at %s percent which is above ' \
                       'the threshold of %s percent.' % 
                       (filesystem, str(usage), str(limit)))
        status = {'status': 'WARN'}
    else:
        logger.info('Disk usage of %s is at %s percent which is above the ' \
                    'threshold of %s percent.' % 
                    (filesystem, str(usage), str(limit)))
        status = {'status': 'OK'}
    service_request('disk_space', 'PUT', status)

def check_swap_usage(limit):
    swap_total = local("free | grep -i swap | awk '{print $2}'")
    swap_used = local("free | grep -i swap | awk '{print $3}'")
    usage = float(swap_used)/float(swap_total) * 100
    if (usage > float(limit)):
        logger.warning('Swap usage is a %s percent which is above the ' \
                       'threshold of %s percent.' % (str(usage), str(limit)))
        status = {'status': 'WARN'}
    else:
        logger.info('Swap usage is a %s percent which is below the ' \
                    'threshold of %s percent.' % (str(usage), str(limit)))
        status = {'status': 'OK'}
    service_request('swap_usage', 'PUT', status)

def check_io_wait_time(limit):
    iowait = local("vmstat | grep -v [a-z] | awk '{print $16}'").rstrip()
    if (float(iowait) > float(limit)):
        logger.warning('IO wait times are at %s percent which is above the ' \
                       'threshold of %s percent.' % (str(iowait), str(limit)))
        status = {'status': 'WARN'}
    else:
        logger.info('IO wait times are at %s percent which is below the ' \
                    'threshold of %s percent.' % (str(iowait), str(limit)))
        status = {'status': 'OK'}
    service_request('io_wait_time', 'PUT', status)

def check_mysql(slow_query_limit, memory_usage, innodb_memory_usage, threads):
    with settings(warn_only=True):
        messages = list()
        report = local('mysqlreport')
        if report.failed:
            logger.warning('mysql server does not appear to be running: %s' % 
                           report)
            status = {'status': 'ERR'}
        else:
          for line in report.splitlines():
              #check for slow wait times:
              if ('Slow' in line and 'Log' in line):
                  if (float(line.split()[5]) > float(slow_query_limit)):
                      messages.append('MYSQL slow queries is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], str(slow_query_limit)))
                  else:
                      messages.append('MYSQL slow queries is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], str(slow_query_limit)))

              #check overall memory usage
              elif ('Memory usage' in line):
                  if (float(line.split()[6]) > float(memory_usage)):
                      messages.append('MYSQL memory usage is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[6], str(memory_usage)))
                  else:
                      messages.append('MYSQL memory usage is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[6], str(memory_usage)))

              #check InnoDB memory usage
              elif ('Usage' in line and 'Used' in line):
                  if (float(line.split()[5]) > float(innodb_memory_usage)):
                      messages.append('InnoDB memory usage is %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], 
                                       str(innodb_memory_usage)))
                  else:
                      messages.append('InnoDB memory usage is %s percent ' \
                                      'which is below the threshold of %s ' \
                                      'percent.' % 
                                      (line.split()[5], 
                                       str(innodb_memory_usage)))

              #check thread usage
              elif ('Max used' in line):
                  if (float(line.split()[6]) > float(threads)):
                      messages.append('Thread usage is %s percent which is ' \
                                      'above the threshold of %s percent.' % 
                                      (line.split()[6], str(threads)))
                  else:
                      messages.append('Thread usage is %s percent which is ' \
                                      'below the threshold of %s percent.' % 
                                      (line.split()[6], str(threads)))
                 
          message = ' '.join(messages)
          if 'above' in message: 
              logger.warning(message)
              status = {'status': 'WARN'}
          else:
              logger.info(message)
              status = {'status': 'OK'}
    service_request('mysql', 'PUT', status)

def check_ldap():
    try:
        local('ldapsearch -H ldap://auth.getpantheon.com -x -ZZ')
    except:
        logger.exception('Cannot connect to LDAP on localhost.')
        status = {'status': 'ERR'}
    else:
        logger.info('ldap responded')
        status = {'status': 'OK'}
    service_request('ldap', 'PUT', status)

def check_apache(url):
    _test_url('apache',url)

def check_varnish(url):
    _test_url('varnish',url)

def check_pound_via_apache(url):
    _test_url('pound',url)

def check_pound_via_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        logger.exception('Cannot connect to Pound on %s at %s.' % 
                         ('localhost', str(port)))
        status = {'status': 'ERR'}
        service_request('pound_socket', 'PUT', status)
    else:
        logger.info('pound responded')
        status = {'status': 'OK'}
        service_request('pound_socket', 'PUT', status)

def check_memcached(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        logger.exception('Cannot connect to Memcached on %s %s.' % 
                         ('localhost', str(port)))
        status = {'status': 'ERR'}
        service_request('memcached', 'PUT', status)
    else:
        logger.info('memcached responded')
        status = {'status': 'OK'}
        service_request('memcached', 'PUT', status)

def _test_url(service, url):
    code = urllib.urlopen(url).code
    if (code >=  400):
        logger.warning('%s returned an error code of %s.' % (service, code))
        status = {'status': 'ERR'}
    else:
        logger.info('%s returned an error code of %s.' % (service, code))
        status = {'status': 'OK'}
    service_request(service, 'PUT', status)
# TODO: figure out what to search for from the following output
#    print(connection.info())
#    print(connection.read())
