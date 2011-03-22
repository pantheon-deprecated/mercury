import os
from lxml import etree

class Junit():
    def __init__(self, sn, cn):
        self.sn = sn.capitalize()
        self.cn = "test%s" % cn.capitalize()

    def success(self, msg):
        """ Create a junit file for a passed test
            msg: The message to add
        """
        suites = self._base_xml()
        ts = self._get_suite(suites)
        if ts is None:
            ts = etree.SubElement(suites, "testsuite", name=self.sn)
        tc = self._get_case(ts)
        if tc is None:
            tc = etree.SubElement(ts, "testcase", name=self.cn)
        tc.text = '\n'.join([tc.text, msg]) if tc.text else msg
        self._write_junit_file(suites)

    def fail(self, msg):
        """ Create a junit file for a failed test
            msg: The message to add
        """
        suites = self._base_xml()
        ts = self._get_suite(suites)
        if ts is None:
            ts = etree.SubElement(suites, "testsuite", name=self.sn)
        tc = self._get_case(ts)
        if tc is None:
            tc = etree.SubElement(ts, "testcase", name=self.cn)
        fail = etree.SubElement(tc, "failure")
        fail.text = msg
        self._write_junit_file(suites)

    def error(self, msg):
        """ Create a junit file for a error
            msg: The message to add
        """
        suites = self._base_xml()
        ts = self._get_suite(suites)
        if ts is None:
            ts = etree.SubElement(suites, "testsuite", name=self.sn)
        tc = self._get_case(ts)
        if tc is None:
            tc = etree.SubElement(ts, "testcase", name=self.cn)
        fail = etree.SubElement(tc, "error")
        fail.text = msg
        self._write_junit_file(suites)

    def _get_suite(self, suites):
        return suites.find("testsuite[@name='%s']" % self.sn)

    def _get_case(self, suite):
        return suite.find("testcase[@name='%s']" % self.cn)

    def _base_xml(self):
        """ Creates the base xml doc structure
            suitename: Name used for the testsuite.
        """
        try:
            f = open(os.path.join(get_workspace(), "results.xml"), 'r')
        except:
            doc = etree.Element("testsuites")
            return doc
        else:
            parser = etree.XMLParser(remove_blank_text=True)
            doc = etree.parse(f, parser)
            f.close()
            return doc.getroot()

    def _write_junit_file(self, doc):
        """ Write a new junit file
            doc: The Element Tree object to write to a file
        """
        doc = etree.ElementTree(doc)
        with open(os.path.join(get_workspace(), "results.xml"), 'w') as f:
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
