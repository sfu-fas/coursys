import unittest
from coredata.models import *

class CoredataTestCase(unittest.TestCase):
    def setUp(self):
        pass
    
    def testCreate(self):
        p = Person.objects.create(emplid=200012345, userid="test1",
                lastname="Lname", firstnames="Fname M")
        self.assertEquals(str(p), "Lname, Fname M (200012345)")

