import os
from lxml import etree

def validate_content(testcase, data, page_descr="unknown page"):
    """
    Validate data as XHTML 1.0 (strict).
    
    testcase should be a unittest.TestCase object (or similar).
    """
    try:
        parser = etree.XMLParser(dtd_validation=True, no_network=True)
        etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as e:
        #print "-"*40
        #print data
        #print "-"*40
        testcase.fail("Invalid XHTML produced in %s:\n  %s" % (page_descr, str(e)))

