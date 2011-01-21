import os

from xml.dom.minidom import Document

import postback

def junit_pass(status, name='Pantheon'):
    """Create a junit file (or entry in exiting file???) for a passed test

    """
    doc = _base_xml(name)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "testPass")
    txt = doc.createTextNode(status['pass'])
    testcase.appendChild(status)
    testsuite.appendChild(testcase)
    _write_junit_file(doc)

def junit_failure(name, message):
    """For failures
    """
    pass

def junit_error(name, message):
    """For errors
    """
    pass

def _base_xml(name):
    doc = Document()
    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)
    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", name)
    testsuites.appendChild(testsuite)
    return doc

def _write_junit_file(result_file='results.xml'):
    """Write a new junit file or append to an existing???

    """
    with open(os.path.join(postback.get_workspace(), result_file), 'w') as f:
        f.write(doc.toprettyxml(indent="  "))
        f.close()

