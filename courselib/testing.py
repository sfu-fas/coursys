import os
from xml.parsers.xmlproc import xmlproc, xmlval

class CountingErrorHandler(xmlproc.xmlapp.ErrorHandler):
    """
    xmlproc error handler that counts and reports errors
    """
    def __init__(self,locator):
        self.count = 0
        xmlproc.xmlapp.ErrorHandler.__init__(self, locator)
        
    def fatal(self,msg):
        self.count += 1
        if self.locator==None:
            print "ERROR: "+msg
        else:
            print "ERROR: "+msg+" at %s:%d:%d" % (self.locator.get_current_sysid(),\
                                                  self.locator.get_line(),\
                                                  self.locator.get_column())

def validate_content(testcase, data):
    """
    Validate data as XHTML 1.0 (strict); returns count of errors.
    
    testcase should be a unittest.TestCase object (or similar).
    """
    # use a local copy of the DTD
    dtd = os.path.join(os.getcwd(), "courselib/dtd", "xhtml1-strict.dtd")
    data_system = data.replace("http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd", dtd, 1)
    assert data != data_system
    
    # run through the validator
    parser = xmlval.XMLValidator()
    parser.set_application(xmlproc.Application())
    #parser.reset()
    errs = CountingErrorHandler(parser)
    parser.set_error_handler(errs)
    parser.feed(data)
    
    if errs.count > 0:
        print "-"*40
        print data
        print "-"*40
        testcase.fail("Invalid XHTML produced.")

