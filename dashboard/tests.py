from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL

from coredata.tests import create_offering
from coredata.models import CourseOffering

class DashboardTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_front_page(self):
        client = Client()
        client.login(ticket="0kvm", service=CAS_SERVER_URL)

        response = client.get("/")
        self.assertEquals(response.status_code, 200)
        
        # this student is in this course: check for a link to its page
        c = CourseOffering.objects.get(slug='1101-cmpt-125-d200')
        self.assertContains(response, '<a href="%s"' % (c.get_absolute_url()) )

        #print response.content


    def test_course_page(self):
        """
        Check out a course front-page
        """
        s, c = create_offering()
        
        client = Client()
        client.login(ticket="0kvm", service=CAS_SERVER_URL)

        response = client.get(c.get_absolute_url())
        #self.assertEquals(response.status_code, 200)
        

        

