import os
from lxml import etree

class Junit():
    def __init__(self, suitename, casename):
        self.suitename = suitename.capitalize()
        self.casename = "test%s" % casename.capitalize()
        self.workspace = get_workspace()

    def success(self, msg):
        """ Create a junit file for a passed test
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        case.text = '\n'.join([case.text, msg]) if case.text else msg
        self._write_junit_file(suites)

    def fail(self, msg):
        """ Create a junit file for a failed test
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        fail = self._get_fail(case)
        fail.text = '\n'.join([fail.text, msg]) if fail.text else msg
        self._write_junit_file(suites)

    def error(self, msg):
        """ Create a junit file for a error
            msg: The message to add
        """
        suites = self._base_xml()
        suite = self._get_suite(suites)
        case = self._get_case(suite)
        error = self._get_error(case)
        error.text = '\n'.join([error.text, msg]) if error.text else msg
        self._write_junit_file(suites)

    def _get_fail(self, case):
        fail = case.find("failure")
        if fail is None:
            return etree.SubElement(case, "failure")
        return fail

    def _get_error(self, case):
        error = case.find("error")
        if error is None:
            return etree.SubElement(case, "error")
        return error

    def _get_suite(self, suites):
        suite = suites.find("testsuite[@name='%s']" % self.suitename)
        if suite is None:
            return etree.SubElement(suites, "testsuite", name=self.suitename)
        return suite

    def _get_case(self, suite):
        case = suite.find("testcase[@name='%s']" % self.casename)
        if case is None:
            return etree.SubElement(suite, "testcase", name=self.casename)
        return case

    def _base_xml(self):
        """ Creates the base xml doc structure
            suitename: Name used for the testsuite.
        """
        try:
            f = open(os.path.join(self.workspace, "results.xml"), 'r')
        except:
            doc = etree.Element("testsuites")
            return doc
        else:
            doc = etree.parse(f)
            f.close()
            return doc.getroot()

    def _write_junit_file(self, doc):
        """ Write a new junit file
            doc: The Element Tree object to write to a file
        """
        doc = etree.ElementTree(doc)
        with open(os.path.join(self.workspace, "results.xml"), 'w') as f:
            doc.write(f, xml_declaration=True, pretty_print=True)

def get_workspace():
    """Return the workspace to store build data information.

    If being run from CLI (not jenkins) use alternate path (so data can still
    be sent back to Atlas, regardless of how job is run).

    """
    workspace = os.environ.get('WORKSPACE')
    if workspace:
        return workspace
    else:
        return '/etc/pantheon/jenkins/workspace'
