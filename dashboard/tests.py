from django.test import TestCase

from coredata.tests import create_offering
from coredata.models import *
from dashboard.models import UserConfig
from courselib.testing import *
from django.core.urlresolvers import reverse
import re, datetime

class DashboardTest(TestCase):
    fixtures = ['test_data']
    def setUp(self):
        self.c_slug = TEST_COURSE_SLUG

    def test_front_page(self):
        # log in as student in the course
        userid = Member.objects.filter(offering__slug=self.c_slug, role="STUD")[0].person.userid
        client = Client()
        client.login_user(userid)

        response = client.get("/")
        self.assertEquals(response.status_code, 200)
        
        # this student is in this course: check for a link to its page (but it only appears after start of semester)
        c = CourseOffering.objects.get(slug=self.c_slug)
        if c.semester.start < datetime.date.today():
            self.assertContains(response, '<a href="%s"' % (c.get_absolute_url()) )

        validate_content(self, response.content, "index page")


    def test_course_page(self):
        """
        Check out a course front-page
        """
        _, c = create_offering()
        
        client = Client()
        # not logged in: should be redirected to login page
        response = client.get(c.get_absolute_url())
        self.assertEquals(response.status_code, 302)

        # log in as student "0aaa0"
        client.login_user("0aaa0")
        p = Person.objects.get(userid="0aaa0")

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
        url = reverse('marking.views.manage_activity_components', kwargs={'course_slug': self.c_slug, 'activity_slug': 'a1'})
        instr = "ggbaker"
        ta = "0grad1"
        student = "0aaa0"
        nobody = "0bbb6"
        
        client = Client()

        # try without logging in
        response = client.get(url)
        self.assertEquals(response.status_code, 302)
        # try as instructor
        client.login_user(instr)
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        validate_content(self, response.content, url)
        # try as TA
        client.login_user(ta)
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        # try as student
        client.login_user(student)
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        # try as non-member
        client.login_user(nobody)
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        
    def test_impersonation(self):
        """
        Test impersonation logic
        """
        client = Client()
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': self.c_slug})

        # login as a sysadmin
        client.login_user('sumo')
        # not instructor, so can't really access
        response = client.get(url)
        self.assertEquals(response.status_code, 403)
        # ...but can impersonate instructor
        response = client.get(url, {"__impersonate": "ggbaker"})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as ggbaker')

        # login as student
        client.login_user("0aaa0")
        # can access normally
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0aaa0')
        # try to impersonate anybody: not allowed
        response = client.get(url, {"__impersonate": "0aaa1"})
        self.assertEquals(response.status_code, 403)
        response = client.get(url, {"__impersonate": "ggbaker"})
        self.assertEquals(response.status_code, 403)

        # login as instructor
        client.login_user("ggbaker")
        # can access course page
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as ggbaker')
        # try to impersonate non-student: not allowed
        response = client.get(url, {"__impersonate": "0bbb0"})
        self.assertEquals(response.status_code, 403)
        # try to impersonate student: should be them
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0aaa0')
        
        # try some other course: shouldn't be able to impersonate
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': '1114-cmpt-310-d100'})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 403)
        # try non-course URL as non-admin: shouldn't be able to impersonate
        client.login_user("diana")
        url = reverse('dashboard.views.index', kwargs={})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEquals(response.status_code, 403)

    def test_userconfig(self):
        """
        Test user configuration
        """
        tokenre = re.compile("^[0-9a-f]{32}$")

        client = Client()
        userid = "0aaa0"
        client.login_user(userid)
        configurl = reverse('dashboard.views.config', kwargs={})
        response = client.get(configurl)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "You do not currently have the external news feed")
        self.assertContains(response, "You do not currently have the external calendar")
        
        # activate calendar
        url = reverse('dashboard.views.create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)

        response = client.get(configurl)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "You do not currently have the external news feed")
        self.assertContains(response, "You can get your calendar as iCalendar")
        
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEquals(len(confs), 1)
        uc = confs[0]
        token = uc.value['token']
        self.assertIsNotNone(tokenre.match(token))
        
        url = reverse('dashboard.views.calendar_ical', kwargs={'token': token, 'userid': userid})
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "BEGIN:VCALENDAR")
        self.assertContains(response, "DTSTART;VALUE=DATE-TIME:20")
        
        # change calendar URL
        url = reverse('dashboard.views.create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEquals(len(confs), 1)
        self.assertNotEqual(token, confs[0].value['token'])
        
        # disable and re-enable calendar URL
        url = reverse('dashboard.views.disable_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEquals(len(confs), 1)
        self.assertTrue('token' not in confs[0].value)
        
        url = reverse('dashboard.views.create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEquals(len(confs), 1)
        self.assertIsNotNone(tokenre.match(confs[0].value['token']))
        


        # activate feed
        url = reverse('dashboard.views.create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)

        response = client.get(configurl)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Your external news feed is currently enabled")
        self.assertContains(response, "You can get your calendar as iCalendar")
        
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEquals(len(confs), 1)
        uc = confs[0]
        token = uc.value['token']
        self.assertIsNotNone(tokenre.match(token))
        
        url = reverse('dashboard.views.atom_feed', kwargs={'token': token, 'userid': userid})
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, '<feed xmlns="http://www.w3.org/2005/Atom">')
        
        # change feed URL
        url = reverse('dashboard.views.create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEquals(len(confs), 1)
        self.assertNotEqual(token, confs[0].value['token'])
        
        # disable and re-enable feed URL
        url = reverse('dashboard.views.disable_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEquals(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEquals(len(confs), 0)
        
        url = reverse('dashboard.views.create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEquals(len(confs), 1)
        self.assertIsNotNone(tokenre.match(confs[0].value['token']))
        


    def test_pages(self):
        person = Person.objects.filter()[0]
        c = Client()
        
        # as instructor
        c.login_user(person.userid)
        test_views(self, c, 'dashboard.views.', ['index', 'index_full', 'news_list', 'config', 'calendar',
                'create_calendar_url', 'disable_calendar_url', 'news_config', 'create_news_url',
                'disable_news_url', 'list_docs', 'photo_agreement'], {})
        test_views(self, c, 'dashboard.views.', ['view_doc'], {'doc_slug': 'impersonate'})

        # admin views for signatures
        r = Role.objects.filter(role='ADMN')[0]
        c.login_user(r.person.userid)
        test_views(self, c, 'dashboard.views.', ['signatures', 'new_signature'], {})


