import os

from fabric.api import local

from pantheon import pantheon
from pantheon import postback
from xml.dom.minidom import Document

def clean_workspace():
    """Cleanup data files from build workspace.

    This should be run before any other processing is done.

    """
    workspace = postback.get_workspace()
    if os.path.exists(workspace):
        local('rm -f %s' % os.path.join(workspace, '*'))

def parse_build_data():
    """Output build messages/warnings/errors to stdout & junit file.

    """
    messages, warnings, errors = _get_build_messages()

    if messages:
        messages = '\n'.join(messages)
        print('\nBuild Messages: \n' + '=' * 30)
        print(messages)
    if warnings:
        warnings = '\n'.join(warnings)
        print('\nBuild Warnings: \n' + '=' * 30)
        print(warnings)
    if errors:
        errors = '\n'.join(errors)
        print('\nBuild Error: \n' + '=' * 30)
        print(errors)

    # Only need JUNIT file if we are in a Hudson build.
    if _in_hudson():
        write_junit_file({'error': errors,'fail': warnings,'pass': messages})

def write_junit_file(status, name='Pantheon'):
    """Creates a junit xml file from build warnings and build errors.
        status = A dictionary of messages from pass, fail or error.
        name = The name to assign to the test suite.
    """
    doc = Document()
    testsuites = doc.createElement("testsuites")
    doc.appendChild(testsuites)
    testsuite = doc.createElement("testsuite")
    testsuite.setAttribute("name", name)
    testsuites.appendChild(testsuite)
    if 'error' in status:
        testcase = doc.createElement("testcase")
        testcase.setAttribute("name", "testError")
        error = doc.createElement("error")
        txt = doc.createTextNode(status['error'])
        error.appendChild(txt)
        testcase.appendChild(error)
        testsuite.appendChild(testcase)
    if 'fail' in status:
        testcase = doc.createElement("testcase")
        testcase.setAttribute("name", "testFail")
        failure = doc.createElement("failure")
        txt = doc.createTextNode(status['fail'])
        failure.appendChild(txt)
        testcase.appendChild(failure)
        testsuite.appendChild(testcase)
    if 'pass' in status:
        testcase = doc.createElement("testcase")
        testcase.setAttribute("name", "testPass")
        txt = doc.createTextNode(status['pass'])
        testcase.appendChild(txt)
        testsuite.appendChild(testcase)

    with open(os.path.join(postback.get_workspace(),'results.xml'), 'w') as f:
        f.write(doc.toprettyxml(indent="  "))
        f.close()

def _get_build_messages():
    """Return the build messages/warnings/errors.
    """
    data = postback.get_build_data()
    return (data.get('build_messages'),
            data.get('build_warnings'),
            data.get('build_error'))

def _in_hudson():
    """If inside a Hudson build, return True.

    """
    # If the 'BUILD_TAG' environment var exists, assume we are in Hudson.
    return bool(os.environ.get('BUILD_TAG'))

