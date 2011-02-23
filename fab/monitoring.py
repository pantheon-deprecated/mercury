# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import pdb
import smtplib
import socket
import urllib
import traceback
import syslog

from fabric.api import *

syslog.openlog('monitoring')

def check_load_average(limit):
    loads = os.getloadavg()
    if (float(loads[0]) > float(limit)):
        syslog.syslog(syslog.LOG_ERR, 'Load average is %s which is above the' \
                                      ' threshold of %s.' % 
                                      (str(loads[0]), str(limit)))
    else:
        syslog.syslog(syslog.LOG_INFO, 'Load average is %s which is below' \
                                       ' the threshold of %s.' % 
                                       (str(loads[0]), str(limit)))


def check_disk_space(filesystem, limit):
    s = os.statvfs(filesystem)
    usage = (s.f_blocks - s.f_bavail)/float(s.f_blocks) * 100
    if (float(usage) > float(limit)):
        syslog.syslog(syslog.LOG_ERR, 'Disk usage of %s is at %s percent ' \
                                      'which is above the threshold of %s ' \
                                      'percent.' % 
                                      (filesystem, str(usage), str(limit)))
    else:
        syslog.syslog(syslog.LOG_INFO, 'Disk usage of %s is at %s percent' \
                                       ' which is above the threshold of %s' \
                                       ' percent.' % 
                                       (filesystem, str(usage), str(limit)))


def check_swap_usage(limit):
    swap_total = local("free | grep -i swap | awk '{print $2}'")
    swap_used = local("free | grep -i swap | awk '{print $3}'")
    usage = float(swap_used)/float(swap_total) * 100
    if (usage > float(limit)):
        syslog.syslog(syslog.LOG_ERR, 'Swap usage is a %s percent which is' \
                                      ' above the threshold of %s percent.' % 
                                      (str(usage), str(limit)))
    else:
        syslog.syslog(syslog.LOG_INFO, 'Swap usage is a %s percent which is ' \
                                       'below the threshold of %s percent.' % 
                                       (str(usage), str(limit)))


def check_io_wait_time(limit):
    iowait = local("vmstat | grep -v [a-z] | awk '{print $16}'").rstrip()
    if (float(iowait) > float(limit)):
        syslog.syslog(syslog.LOG_ERR, 'IO wait times are at %s percent which ' \
                                      'is above the threshold of %s percent.' % 
                                      (str(iowait), str(limit)), 'IOWaitTime')
    else:
        syslog.syslog(syslog.LOG_INFO, 'IO wait times are at %s percent ' \
                                       'which is below the threshold of %s ' \
                                       'percent.' % (str(iowait), str(limit)))


def check_mysql(slow_query_limit, memory_usage, innodb_memory_usage, threads):
    with settings(warn_only=True):
        messages = list()
        report = local('mysqlreport')
        if report.failed:
            syslog.syslog(syslog.LOG_ERR, 'mysql server does not appear to ' \
                                          'be running: %s' % report)
        for line in report.splitlines():
            #check for slow wait times:
            if ('Slow' in line and 'Log' in line):
                if (float(line.split()[5]) > float(slow_query_limit)):
                    messages.append('MYSQL slow queries is %s percent which ' \
                                    'is above the threshold of %s percent.' % 
                                    (line.split()[5], str(slow_query_limit)))
                else:
                    messages.append('MYSQL slow queries is %s percent which ' \
                                    'is below the threshold of %s percent.' % 
                                    (line.split()[5], str(slow_query_limit)))

            #check overall memory usage
            elif ('Memory usage' in line):
                if (float(line.split()[6]) > float(memory_usage)):
                    messages.append('MYSQL memory usage is %s percent which ' \
                                    'is above the threshold of %s percent.' % 
                                    (line.split()[6], str(memory_usage)))
                else:
                    messages.append('MYSQL memory usage is %s percent which ' \
                                    'is below the threshold of %s percent.' % 
                                    (line.split()[6], str(memory_usage)))

            #check InnoDB memory usage
            elif ('Usage' in line and 'Used' in line):
                if (float(line.split()[5]) > float(innodb_memory_usage)):
                    messages.append('InnoDB memory usage is %s percent which' \
                                    ' is above the threshold of %s percent.' % 
                                    (line.split()[5], str(innodb_memory_usage)))
                else:
                    messages.append('InnoDB memory usage is %s percent which' \
                                    ' is below the threshold of %s percent.' % 
                                    (line.split()[5], str(innodb_memory_usage)))

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
            syslog.syslog(syslog.LOG_ERR, message)
        else:
            syslog.syslog(syslog.LOG_INFO, message)


def check_ldap():
    try:
        local('ldapsearch -H ldap://auth.getpantheon.com -x -ZZ')
    except:
        syslog.syslog(syslog.LOG_ERR, 'Cannot connect to LDAP on localhost.')
        print(traceback.format_exc())
        raise
    else:
        syslog.syslog(syslog.LOG_INFO, 'ldap responded')


def check_apache(url):
    _test_url('Apache',url)


def check_varnish(url):
    _test_url('Varnish',url)


def check_pound_via_apache(url):
    _test_url('Pound',url)


def check_pound_via_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        syslog.syslog(syslog.LOG_ERR, 'Cannot connect to Pound on %s at %s.' % 
                                      ('localhost', str(port)))
        print(traceback.format_exc())
        raise
    else:
        syslog.syslog(syslog.LOG_INFO, 'pound responded')


def check_memcached(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
    except:
        syslog.syslog(syslog.LOG_ERR, 'Cannot connect to Memcached on %s ' \
                                       '%s.' % ('localhost', str(port)))
        print(traceback.format_exc())
        raise
    else:
        syslog.syslog(syslog.LOG_INFO, 'memcached responded')


def _test_url(service, url):
    status = urllib.urlopen(url).code
    if (status >=  400):
        syslog.syslog(syslog.LOG_ERR, '%s returned an error code of %s.' % 
                                      (service, status))
    else:
        syslog.syslog(syslog.LOG_INFO, '%s returned an error code of %s.' % 
                                       (service, status))
# TODO: figure out what to search for from the following output
#    print(connection.info())
#    print(connection.read())
