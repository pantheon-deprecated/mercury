# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import pdb
import smtplib
import socket
import urllib

from fabric.api import *
from xml.dom.minidom import Document


def check_for_script_updates():
    message = local('git pull')
    if 'Already' in message:
        _success(message)
    else:
        _error(message)

def check_for_package_updates():
    local('apt-get update')
    message = local('apt-get -qqys dist-upgrade')
    if (message):
        _error(message)
    else:
        _success('No updates found')


def check_load_average(limit):
    loads = os.getloadavg()
    if (float(loads[0]) > float(limit)):
        _error('Load average is %s which is above the threshold of %s.' % (str(loads[0]), str(limit)))
    else:
        _success('Load average is %s which is below the threshold of %s.' % (str(loads[0]), str(limit)))


def check_disk_space(filesystem, limit):
    s = os.statvfs(filesystem)
    usage = (s.f_blocks - s.f_bavail)/float(s.f_blocks) * 100
    if (float(usage) > float(limit)):
        _error('Disk usage of %s is at %s percent which is above the threshold of %s percent.' % (filesystem, str(usage), str(limit)))
    else:
        _success('Disk usage of %s is at %s percent which is above the threshold of %s percent.' % (filesystem, str(usage), str(limit)))


def check_swap_usage(limit):
    swap_total = local("free | grep -i swap | awk '{print $2}'")
    swap_used = local("free | grep -i swap | awk '{print $3}'")
    usage = float(swap_used)/float(swap_total) * 100
    if (usage > float(limit)):
        _error('Swap usage is a %s percent which is above the threshold of %s percent.' % (str(usage), str(limit)))
    else:
        _success('Swap usage is a %s percent which is below the threshold of %s percent.' % (str(usage), str(limit)))


def check_io_wait_time(limit):
    iowait = local("vmstat | grep -v [a-z] | awk '{print $16}'").rstrip()
    print('iowait is' + iowait)
    if (float(iowait) > float(limit)):
        _error('IO wait times are at %s percent which is above the threshold of %s percent.' % (str(iowait), str(limit)))
    else:
        _success('IO wait times are at %s percent which is below the threshold of %s percent.' % (str(iowait), str(limit)))


def check_mysql(slow_query_limit, memory_usage, innodb_memory_usage, threads):
    with settings(warn_only=True):
        messages = list()
        report = local('mysqlreport')
        if report.failed:
            _fail('mysql server does not appear to be running: %s' % report)
        for line in report.splitlines():
            #check for slow wait times:
            if ('Slow' in line and 'Log' in line):
                if (float(line.split()[5]) > float(slow_query_limit)):
                    messages.append('MYSQL slow queries is %s percent which is above the threshold of %s percent.' % (line.split()[5], str(slow_query_limit)))
                else:
                    messages.append('MYSQL slow queries is %s percent which is below the threshold of %s percent.' % (line.split()[5], str(slow_query_limit)))

            #check overall memory usage
            elif ('Memory usage' in line):
                if (float(line.split()[6]) > float(memory_usage)):
                    messages.append('MYSQL memory usage is %s percent which is above the threshold of %s percent.' % (line.split()[6], str(memory_usage)))
                else:
                    messages.append('MYSQL memory usage is %s percent which is below the threshold of %s percent.' % (line.split()[6], str(memory_usage)))

            #check InnoDB memory usage
            elif ('Usage' in line and 'Used' in line):
                if (float(line.split()[5]) > float(innodb_memory_usage)):
                    messages.append('InnoDB memory usage is %s percent which is above the threshold of %s percent.' %(line.split()[5], str(innodb_memory_usage)))
                else:
                    messages.append('InnoDB memory usage is %s percent which is below the threshold of %s percent.' %(line.split()[5], str(innodb_memory_usage)))

            #check thread usage
            elif ('Max used' in line):
                if (float(line.split()[6]) > float(threads)):
                    messages.append('Thread usage is %s percent which is above the threshold of %s percent.' % (line.split()[6], str(threads)))
                else:
                    messages.append('Thread usage is %s percent which is below the threshold of %s percent.' % (line.split()[6], str(threads)))
               
        message = ' '.join(messages)
        if 'above' in message: 
            _error(message)
        else:
            _success(message)


def check_ldap():
    try:
        local('ldapsearch -H ldap://auth.getpantheon.com -x -ZZ')
        _success('ldap responded')
    except:
        _fail('Cannot connect to LDAP on localhost.')


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
        _success('pound responded')
    except:
        _fail('Cannot connect to Pound on %s %s.' % ('localhost', str(port)))


def check_memcached(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        port = int(port)
        s.connect(('localhost', port))
        s.shutdown(2)
        _success('memcached responded')
    except:
        _fail('Cannot connect to Memcached on %s %s.' % ('localhost', str(port)))


def _test_url(service, url):
    connection = urllib.urlopen(url)
    status = connection.getcode()
    if (status >=  400):
        _error('%s returned an error code of %s.' % (service, status))
    else:
        _success('%s returned an error code of %s.' % (service, status))
# TODO: figure out what to search for from the following output
#    print(connection.info())
#    print(connection.read())


def _success(message):
    f = open(os.environ.get('WORKSPACE') + '/results.xml', 'w')

    doc = Document()

    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)

    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", "MyTest")
    testsuite.setAttribute("file", ".")
    testsuite.setAttribute("tests", "1")
    testsuite.setAttribute("assertions", "0")
    testsuite.setAttribute("failures", "0")
    testsuite.setAttribute("errors", "0")
    testsuite.setAttribute("time", "1")
    testsuites.appendChild(testsuite)   

    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "error")
    testcase.setAttribute("assertions", "0")
    testcase.setAttribute("time", "1")
    testsuite.appendChild(testcase)

    etext = doc.createTextNode(message)
    testcase.appendChild(etext)

    f.write(doc.toprettyxml(indent="  "))
    f.close()

    #now print so we see it in hudson console output
    print(message)


def _error(message):
    f = open(os.environ.get('WORKSPACE') + '/results.xml', 'w')

    doc = Document()

    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)

    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", "MyTest")
    testsuite.setAttribute("file", ".")
    testsuite.setAttribute("tests", "1")
    testsuite.setAttribute("assertions", "0")
    testsuite.setAttribute("failures", "0")
    testsuite.setAttribute("errors", "1")
    testsuite.setAttribute("time", "1")
    testsuites.appendChild(testsuite)   

    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "error")
    testcase.setAttribute("assertions", "0")
    testcase.setAttribute("time", "1")
    testsuite.appendChild(testcase)

    error = doc.createElement("error")
    testcase.appendChild(error)

    etext = doc.createTextNode(message)
    error.appendChild(etext)

    f.write(doc.toprettyxml(indent="  "))
    f.close()

    #now print so we see it in hudson console output
    print(message)


def _fail(message):
    f = open(os.environ.get('WORKSPACE') + '/results.xml', 'w')

    doc = Document()

    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)

    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", "MyTest")
    testsuite.setAttribute("file", ".")
    testsuite.setAttribute("tests", "1")
    testsuite.setAttribute("assertions", "0")
    testsuite.setAttribute("failures", "1")
    testsuite.setAttribute("errors", "0")
    testsuite.setAttribute("time", "1")
    testsuites.appendChild(testsuite)   

    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "error")
    testcase.setAttribute("assertions", "0")
    testcase.setAttribute("time", "1")
    testsuite.appendChild(testcase)

    failure = doc.createElement("failure")
    testcase.appendChild(failure)

    etext = doc.createTextNode(message)
    failure.appendChild(etext)

    f.write(doc.toprettyxml(indent="  "))
    f.close()

    #now print so we see it in hudson console output
    print(message)
