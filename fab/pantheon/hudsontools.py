import os

from xml.dom.minidom import Document
from xml.dom.minidom import parse

def junit_pass(msg, suitename, casename=None):
    """ Create a junit file for a passed test
        msg: The message to add
        suitename: Name used for the testsuite.
        casename: Name used for the testcase.
    """
    if not casename:
        casename = suitename
    doc = _base_xml(suitename)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % casename)
    txt = doc.createTextNode(msg)
    testcase.appendChild(txt)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, suitename)

def junit_fail(msg, suitename, casename=None):
    """ Create a junit file for a failed test
        msg: The message to add
        suitename: Name used for the testsuite.
        casename: Name used for the testcase.
    """

    if not casename:
        casename = suitename
    doc = _base_xml(suitename)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % casename)
    failure = doc.createElement("failure")
    txt = doc.createTextNode(msg)
    failure.appendChild(txt)
    testcase.appendChild(failure)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, suitename)

def junit_error(msg, suitename, casename=None):
    """ Create a junit file for a error
        msg: The message to add
        suitename: Name used for the testsuite.
        casename: Name used for the testcase.
    """

    if not casename:
        casename = suitename
    doc = _base_xml(suitename)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % casename)
    error = doc.createElement("error")
    txt = doc.createTextNode(msg)
    error.appendChild(txt)
    testcase.appendChild(error)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, suitename)

def _base_xml(suitename):
    """ Creates the base xml doc structure
        suitename: Name used for the testsuite.
    """
    try:
        f = open(os.path.join(get_workspace(), "%s.xml" % suitename), 'r')
    except:
        doc = Document()
        testsuites = doc.createElement("testsuites")
        doc.appendChild(testsuites)
        testsuite = doc.createElement("testsuite")
        testsuite.setAttribute("name", suitename)
        testsuites.appendChild(testsuite)
    else:
        doc = parse(f)
        f.close()
    return doc

def _write_junit_file(doc, filename='results'):
    """ Write a new junit file
        doc: The structured xml document to write to a file
        filename: The filename for the junit report
    """
    with open(os.path.join(get_workspace(), "%s.xml" % filename), 'w') as f:
        f.write(doc.toprettyxml(indent="  "))

def get_workspace():
    """Return the workspace to store build data information.

    If being run from CLI (not hudson) use alternate path (so data can still
    be sent back to Atlas, regardless of how job is run).

    """
    workspace = os.environ.get('WORKSPACE')
    if workspace:
        return workspace
    else:
        return '/etc/pantheon/hudson/workspace'
