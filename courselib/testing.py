import os
from lxml import etree
import urllib

# course with the test data
TEST_COURSE_SLUG = '2012su-cmpt-383-d1'

def validate_content(testcase, data, page_descr="unknown page"):
    """
    Validate data as XHTML 1.0 (strict).
    
    testcase should be a unittest.TestCase object (or similar).
    page_descr should be a human-readable description of the page being tested.
    """
    # force use of local copy of DTD
    dtdpath = os.path.join(os.getcwd(), "courselib", "dtd", "xhtml1-strict.dtd")
    dtdpath = dtdpath.replace("\\", "/")
    dtdpath = urllib.quote(dtdpath)
    
    dtd = '<!DOCTYPE html SYSTEM "%s">' % dtdpath
    data_system = data.replace('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">', dtd, 1)
    assert data != data_system
    
    try:
        parser = etree.XMLParser(dtd_validation=True, no_network=True)
        etree.fromstring(data_system, parser=parser)
    except etree.XMLSyntaxError as e:
        #print "-"*40
        #print data
        #print "-"*40
        fh = open("tmp-validation.html", "w")
        fh.write(data)
        fh.close()
        testcase.fail("Invalid XHTML produced in %s:\n  %s" % (page_descr, str(e)))

def basic_page_tests(testcase, client, url):
    """
    Run basic tests on the page: 200 OK, validity.
    """
    response = client.get(url)
    testcase.assertEquals(response.status_code, 200)
    validate_content(testcase, response.content, url)
    return response
