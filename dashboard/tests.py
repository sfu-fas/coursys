from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL

from coredata.tests import create_offering
from coredata.models import *

class DashboardTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_front_page(self):
        # log in as student "0kvm"
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
        # not logged in: should be redirected to login page
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 302)

        # log in as student "0kvm"
        client.login(ticket="0kvm", service=CAS_SERVER_URL)
        p = Person.objects.get(userid="0kvm")

        # not in the course: should get 403 Forbidden
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 403)
        
        # add to course and try again
        m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
        m.save()
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 200)

        # dropped students should be forbidden
        m.role="DROP"
        m.save()
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 403)



