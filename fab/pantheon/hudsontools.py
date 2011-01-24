import os
import postback

from xml.dom.minidom import Document

def junit_pass(msg, name):
    """ Create a junit file for a passed test
        msg: The message to add
        name: Name used for the testsuite, testcase and xml filename
    """
    doc = _base_xml(name)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % name)
    txt = doc.createTextNode(msg)
    testcase.appendChild(txt)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, name)

def junit_failure(msg, name):
    """ Create a junit file for a failed test
        msg: The message to add
        name: Name used for the testsuite, testcase and xml filename
    """
    doc = _base_xml(name)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % name)
    failure = doc.createElement("failure")
    txt = doc.createTextNode(msg)
    failure.appendChild(txt)
    testcase.appendChild(failure)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, name)

def junit_error(msg, name):
    """ Create a junit file for a error
        msg: The message to add
        name: Name used for the testsuite, testcase and xml filename
    """
    doc = _base_xml(name)
    testcase = doc.createElement("testcase")
    testcase.setAttribute("name", "test%s" % name)
    error = doc.createElement("error")
    txt = doc.createTextNode(msg)
    error.appendChild(txt)
    testcase.appendChild(error)
    testsuite = doc.getElementsByTagName('testsuite')[0]
    testsuite.appendChild(testcase)
    _write_junit_file(doc, name)

def _base_xml(name):
    """ Creates the base xml doc structure
        name: Name used for the testsuite, testcase and xml filename
    """
    doc = Document()
    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)
    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", name)
    testsuites.appendChild(testsuite)
    return doc

def _write_junit_file(doc, filename='results'):
    """ Write a new junit file
        doc: The structured xml document to write to a file
        filename: The filename for the junit report
    """
    with open(os.path.join(postback.get_workspace(), "%s.xml" % filename), 'w') as f:
        f.write(doc.toprettyxml(indent="  "))
        f.close()

