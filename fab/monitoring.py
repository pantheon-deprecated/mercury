# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import socket
import urllib
import ConfigParser

from pantheon import logger

from fabric.api import *

# Get our own logger
log = logger.logging.getLogger('monitor')

cfg = ConfigParser.ConfigParser()
conf_file = '/etc/pantheon/services.status'
try:
    cfg.readfp(open(conf_file))
except IOError:
    log.exception('There was an error while loading the configuration file.')
except:
    log.exception('FATAL: Unhandled exception')
    raise

def check_load_average(limit=None):
    """ Check system load average.
    limit: int. Threshold

    """
    section = 'load_average'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    loads = os.getloadavg()
    if (float(loads[0]) > float(limit)):
        log.warning('Load average is %s which is above the threshold of %s.' % 
                    (str(loads[0]), str(limit)))
    else:
        log.info('Load average is %s which is below the threshold of %s.' % 
                 (str(loads[0]), str(limit)))

def check_disk_space(path=None, limit=None):
    """ Check system disk usage.
    path: str. Path to check against
    limit: int. Threshold as percentage.

    """
    section = 'disk_space'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    if not path:
        path = cfg.get(section, 'path')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = os.statvfs(path)
    usage = (s.f_blocks - s.f_bavail)/float(s.f_blocks) * 100
    if (float(usage) > float(limit)):
        log.warning('Disk usage of %s is at %s percent which is above the ' \
                    'threshold of %s percent.' % (path, str(usage), str(limit)))
    else:
        log.info('Disk usage of %s is at %s percent which is above the ' \
                 'threshold of %s percent.' % (path, str(usage), str(limit)))

def check_swap_usage(limit=None):
    """ Check system swap usage.
    limit: int. Threshold as percentage.

    """
    section = 'swap_usage'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    swap_total = local("free | grep -i swap | awk '{print $2}'")
    swap_used = local("free | grep -i swap | awk '{print $3}'")
    usage = float(swap_used)/float(swap_total) * 100
    if (usage > float(limit)):
        log.warning('Swap usage is a %s percent which is above the ' \
                    'threshold of %s percent.' % (str(usage), str(limit)))
    else:
        log.info('Swap usage is a %s percent which is below the ' \
                 'threshold of %s percent.' % (str(usage), str(limit)))

def check_io_wait_time(limit=None):
    """ Check system io wait time.
    limit: int. Threshold as percentage.

    """
    section = 'io_wait_time'
    if not limit:
        limit = cfg.getfloat(section, 'limit')
    log = logger.logging.getLogger('monitor.%s' % section)

    iowait = local("vmstat | grep -v [a-z] | awk '{print $16}'").rstrip()
    if (float(iowait) > float(limit)):
        log.warning('IO wait times are at %s percent which is above the ' \
                    'threshold of %s percent.' % (str(iowait), str(limit)))
    else:
        log.info('IO wait times are at %s percent which is below the ' \
                 'threshold of %s percent.' % (str(iowait), str(limit)))

def check_mysql(slow_query_limit=None, memory_usage=None, innodb_memory_usage=None, threads=None):
    """ Check mysql status.
    sloq_query_limit: int. Threshold as percentage.
    memory_usage: int. Threshold as percentage.
    innodb_memory_usage: int. Threshold as percentage.
    thread: int. Threshold as percentage.

    """
    section = 'mysql'
    if not slow_query_limit:
        slow_query_limit = cfg.getfloat(section, 'slow_query_limit')
    if not memory_usage:
        memory_usage = cfg.getfloat(section, 'memory_usage')
    if not innodb_memory_usage:
        innodb_memory_usage = cfg.getfloat(section, 'innodb_memory_usage')
    if not threads:
        threads = cfg.getfloat(section, 'threads')
    log = logger.logging.getLogger('monitor.%s' % section)

    with settings(warn_only=True):
        messages = list()
        report = local('mysqlreport')
        if report.failed:
            log.warning('mysql server does not appear to be running: %s' % 
                           report)
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
              log.warning(message)
          else:
              log.info(message)

def check_apache(url=None):
    """ Check apache status.
    url: str. Url to test

    """
    section = 'apache'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_varnish(url=None):
    """ Check varnish status.
    url: str. Url to test

    """
    section = 'varnish'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_pound_via_apache(url=None):
    """ Check pound status.
    url: str. Url to test

    """
    section = 'pound'
    if not url:
        url = cfg.get(section, 'url')
    log = logger.logging.getLogger('monitor.%s' % section)

    code = _test_url(url)
    if (code >=  400):
        log.warning('%s returned an error code of %s.' % (section, code))
    else:
        log.info('%s returned a status code of %s.' % (section, code))

def check_pound_via_socket(port=None):
    """ Check pound status.
    port: str. Port to test

    """
    section = 'pound'
    if not port:
        port = cfg.getint(section, 'port')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        log.exception('Cannot connect to Pound on %s at %s.' % 
                      ('localhost', str(port)))
    else:
        log.info('pound responded')

def check_memcached(port=None):
    """ Check memcached status.
    port: str. Port to test

    """
    section = 'memcached'
    if not port:
        port = cfg.getint(section, 'port')
    log = logger.logging.getLogger('monitor.%s' % section)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        log.exception('Cannot connect to Memcached on %s %s.' % 
                      ('localhost', str(port)))
    else:
        log.info('memcached responded')

def _test_url(url):
    """ Test url response code.
    url: str. Url to test

    """
    return urllib.urlopen(url).code

# TODO: figure out what to search for from the following output
#    print(connection.info())
#    print(connection.read())
