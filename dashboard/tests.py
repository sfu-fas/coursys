from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL

from coredata.tests import create_offering
from coredata.models import *
from courselib.testing import *
from django.core.urlresolvers import reverse

class DashboardTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_front_page(self):
        # log in as student "0aaa0"
        client = Client()
        client.login(ticket="0aaa0", service=CAS_SERVER_URL)

        response = client.get("/")
        self.assertEquals(response.status_code, 200)
        
        # this student is in this course: check for a link to its page
        c = CourseOffering.objects.get(slug='1101-cmpt-165-d100')
        self.assertContains(response, '<a href="%s"' % (c.get_absolute_url()) )

        validate_content(self, response.content, "index page")


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
        validate_content(self, response.content, c.get_absolute_url())

        # dropped students should be forbidden
        m.role="DROP"
        m.save()
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 403)

    def test_staff_page(self):
        """
        Check the requires_course_staff_by_slug decorator.
        """
        # a URL and some members/non-members
        url = "/1101-cmpt-165-d100/a1/marking/"
        instr = "ggbaker"
        ta = "0grad"
        student = "0aaa0"
        nobody = "0kvm"
        
        client = Client()

        # try without logging in
        response = client.get(url)
        self.assertEquals(response.status_code, 302)
        # try as instructor
        client.login(ticket=instr, service=CAS_SERVER_URL)
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        validate_content(self, response.content, url)
        # try as TA
        client.login(ticket=ta, service=CAS_SERVER_URL)
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        # try as student
        client.login(ticket=student, service=CAS_SERVER_URL)
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        # try as non-member
        client.login(ticket=nobody, service=CAS_SERVER_URL)
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        
    def test_impersonation(self):
        """
        Test impersonation logic
        """
        client = Client()
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': '1101-cmpt-120-d100'})

        # login as a sysadmin
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        # not instructor, so can't really access
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        # ...but can impersonate instructor
        response = client.get(url, {"__impersonate": "diana"})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as diana')

        # login as student
        client.login(ticket="0bbb0", service=CAS_SERVER_URL)
        # can access normally
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0bbb0')
        # try to impersonate anybody: not allowed
        response = client.get(url, {"__impersonate": "0bbb1"})
        self.assertEquals(response.status_code, 403)
        response = client.get(url, {"__impersonate": "diana"})
        self.assertEquals(response.status_code, 403)

        # login as instructor
        client.login(ticket="diana", service=CAS_SERVER_URL)
        # can access course page
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as diana')
        # try to impersonate non-student: not allowed
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 403)
        # try to impersonate student: should be them
        response = client.get(url, {"__impersonate": "0bbb0"})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0bbb0')
        
        # try some other course: shouldn't be able to impersonate
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': '1101-cmpt-165-d100'})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 403)
        # try non-course URL: shouldn't be able to impersonate
        url = reverse('dashboard.views.index', kwargs={})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 403)

