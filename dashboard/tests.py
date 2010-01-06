from django.test import TestCase
from django.test.client import Client

from coredata.tests import create_offering

class DashboardTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_front_page(self):
        client = Client()
        client.login(username="0kvm", password="")
        #response = client.get("/")
        #print response.content


    def test_course_page(self):
        s, c = create_offering()
        
        client = Client()
        response = client.get(c.get_absolute_url())
        
        #self.assertEquals(response.status_code, 200)
        

        

