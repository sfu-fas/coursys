from coredata.tests import create_offering
from coredata.models import Person, Member, CourseOffering, Role, Semester
from dashboard.models import UserConfig, NewsItem
from courselib.testing import TEST_COURSE_SLUG, Client, validate_content, create_test_offering, test_views, \
    freshen_roles
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from haystack.query import SearchQuerySet
from pages.models import Page, PageVersion
import re, datetime


class DashboardTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_front_page(self):
        # make sure the test semester is reasonably current
        s = CourseOffering.objects.get(slug=TEST_COURSE_SLUG).semester
        today = datetime.date.today()
        s.start = today - datetime.timedelta(days=100)
        s.end = today + datetime.timedelta(days=100)
        s.save()

        # log in as student in the course
        userid = Member.objects.filter(offering__slug=TEST_COURSE_SLUG, role="STUD")[0].person.userid
        client = Client()
        client.login_user(userid)

        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        
        c = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
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
        self.assertEqual(response.status_code, 302)

        # log in as student "0aaa0"
        client.login_user("0aaa0")
        p = Person.objects.get(userid="0aaa0")

        # not in the course: should get 403 Forbidden
        response = client.get(c.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        
        # add to course and try again
        m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
        m.save()
        response = client.get(c.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        validate_content(self, response.content, c.get_absolute_url())

        # dropped students should be forbidden
        m.role="DROP"
        m.save()
        response = client.get(c.get_absolute_url())
        self.assertEqual(response.status_code, 403)

    def test_staff_page(self):
        """
        Check the requires_course_staff_by_slug decorator.
        """
        # force the test course's semester to be "current" so the TA still has access
        semester = CourseOffering.objects.get(slug=TEST_COURSE_SLUG).semester
        today = datetime.date.today()
        semester.start = today
        semester.end = today + datetime.timedelta(days=90)
        semester.save()

        # a URL and some members/non-members
        url = reverse('offering:class_list', kwargs={'course_slug': TEST_COURSE_SLUG})
        instr = "ggbaker"
        ta = Member.objects.filter(offering__slug=TEST_COURSE_SLUG, role='TA')[0].person.userid
        student = "0aaa0"
        nobody = "0bbb6"
        
        client = Client()

        # try without logging in
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        # try as instructor
        client.login_user(instr)
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        validate_content(self, response.content, url)
        # try as TA.
        client.login_user(ta)
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        # try as student
        client.login_user(student)
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
        # try as non-member
        client.login_user(nobody)
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
        # try again as TA, but cheat by changing the semester for the course first.  We also have to change something
        # else, in this case, the section, in order to avoid violating unique constraints when saving it.
        c = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        c.semester = Semester.current()
        c.section = 'q100'
        c.save()
        client.login_user(ta)
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_impersonation(self):
        """
        Test impersonation logic
        """
        freshen_roles()
        client = Client()
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': TEST_COURSE_SLUG})

        # login as a sysadmin
        client.login_user('pba7')
        # not instructor, so can't really access
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
        # ...but can impersonate instructor
        response = client.get(url, {"__impersonate": "ggbaker"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged in as ggbaker')

        # login as student
        client.login_user("0aaa0")
        # can access normally
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0aaa0')
        # try to impersonate anybody: not allowed
        response = client.get(url, {"__impersonate": "0aaa1"})
        self.assertEqual(response.status_code, 403)
        response = client.get(url, {"__impersonate": "ggbaker"})
        self.assertEqual(response.status_code, 403)

        # login as instructor
        client.login_user("ggbaker")
        # can access course page
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged in as ggbaker')
        # try to impersonate non-student: not allowed
        response = client.get(url, {"__impersonate": "dzhao"})
        self.assertEqual(response.status_code, 403)
        # try to impersonate student: should be them
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged in as 0aaa0')
        
        # try some other course: shouldn't be able to impersonate
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': '1114-cmpt-310-d100'})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEqual(response.status_code, 403)
        # try non-course URL as non-admin: shouldn't be able to impersonate
        client.login_user("diana")
        url = reverse('dashboard:index', kwargs={})
        response = client.get(url, {"__impersonate": "0aaa0"})
        self.assertEqual(response.status_code, 403)

    def test_userconfig(self):
        """
        Test user configuration
        """
        tokenre = re.compile("^[0-9a-f]{32}$")

        client = Client()
        userid = "0aaa0"
        client.login_user(userid)
        configurl = reverse('config:config', kwargs={})
        response = client.get(configurl)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You do not currently have the external news feed")
        self.assertContains(response, "You do not currently have the external calendar")
        
        # activate calendar
        url = reverse('config:create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)

        response = client.get(configurl)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You do not currently have the external news feed")
        self.assertContains(response, "You can get your calendar as iCalendar")
        
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEqual(len(confs), 1)
        uc = confs[0]
        token = uc.value['token']
        self.assertIsNotNone(tokenre.match(token))
        
        url = reverse('calendar:calendar_ical', kwargs={'token': token, 'userid': userid})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BEGIN:VCALENDAR")
        self.assertContains(response, "END:VCALENDAR")
        
        # change calendar URL
        url = reverse('config:create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEqual(len(confs), 1)
        self.assertNotEqual(token, confs[0].value['token'])
        
        # disable and re-enable calendar URL
        url = reverse('config:disable_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEqual(len(confs), 1)
        self.assertTrue('token' not in confs[0].value)
        
        url = reverse('config:create_calendar_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        confs = UserConfig.objects.filter(user__userid=userid, key='calendar-config')
        self.assertEqual(len(confs), 1)
        self.assertIsNotNone(tokenre.match(confs[0].value['token']))
        


        # activate feed
        url = reverse('config:create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)

        response = client.get(configurl)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your external news feed is currently enabled")
        self.assertContains(response, "You can get your calendar as iCalendar")
        
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEqual(len(confs), 1)
        uc = confs[0]
        token = uc.value['token']
        self.assertIsNotNone(tokenre.match(token))
        
        url = reverse('news:atom_feed', kwargs={'token': token, 'userid': userid})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<feed xmlns="http://www.w3.org/2005/Atom">')
        
        # change feed URL
        url = reverse('config:create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEqual(len(confs), 1)
        self.assertNotEqual(token, confs[0].value['token'])
        
        # disable and re-enable feed URL
        url = reverse('config:disable_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        self.assertEqual(response.status_code, 302)
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEqual(len(confs), 0)
        
        url = reverse('config:create_news_url', kwargs={})
        response = client.post(url, {'agree': 'on'})
        confs = UserConfig.objects.filter(user__userid=userid, key='feed-token')
        self.assertEqual(len(confs), 1)
        self.assertIsNotNone(tokenre.match(confs[0].value['token']))

    def test_pages(self):
        person = Person.objects.filter(userid__isnull=False)[0]
        c = Client()
        
        # as instructor
        c.login_user(person.userid)
        test_views(self, c, 'dashboard:', ['index', 'index_full'], {})
        test_views(self, c, 'config:', ['config', 'news_config', 'photo_agreement', 'create_calendar_url', 'disable_calendar_url', 'create_news_url', 'disable_news_url'], {})
        test_views(self, c, 'calendar:', ['calendar'], {})
        test_views(self, c, 'news:', ['news_list'], {})
        test_views(self, c, 'docs:', ['list_docs'], {})
        test_views(self, c, 'docs:', ['view_doc'], {'doc_slug': 'impersonate'})

        # admin views for signatures
        freshen_roles()
        r = Role.objects_fresh.filter(role='ADMN')[0]
        c.login_user(r.person.userid)
        test_views(self, c, 'admin:', ['signatures', 'new_signature'], {})


class DatetimeTest(TestCase):
    def setUp(self):
        self.offering = create_test_offering()
        self.instructor = Member.objects.get(offering=self.offering, role='INST').person

    def test_dst(self):
        """
        Test news item in the ambiguous DST switchover
        """
        instr = self.instructor

        n = NewsItem(user=instr, author=instr, source_app='foo', title='The Title',
                     content='Content')
        n.save()

        c = Client()
        c.login_user(instr.userid)
        test_views(self, c, '', ['dashboard:index', 'news:news_list'], {})

        n.published = datetime.datetime(2014, 11, 2, 1, 30, 0) # there are two of this time because of the DST transition
        n.save()

        test_views(self, c, '', ['dashboard:index', 'news:news_list'], {})


class FulltextTest(TestCase):
    """
    Tests of the full-text indexing and searching.
    """
    def setUp(self):
        self.offering = create_test_offering()
        self.instructor = Member.objects.get(offering=self.offering, role='INST')
        call_command('clear_index', interactive=False, verbosity=0)
        self._update_index()

    def _update_index(self):
        call_command('update_index', verbosity=0)

    #def test_search_page(self):
    #    c = Client()
    #    test_views(self, c, 'dashboard.views.', ['site_search'], {}, qs='q=student')

    def test_updating(self):
        """
        Test the way the full text index updates

        The real-time indexing is disabled in the tests environments: slows things down too much. Disabled these tests
        as a result, since they don't really match the deployed or devel behaviour.
        """
        return

        res = SearchQuerySet().models(CourseOffering).filter(text='Babbling')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].object, self.offering)

        # don't expect CourseOfferings to update automatically
        self.offering.title = 'Something Else'
        self.offering.save()
        res = SearchQuerySet().models(CourseOffering).filter(text='Babbling')
        self.assertEqual(len(res), 1)

        # but a manual refresh should find changes
        self._update_index()
        res = SearchQuerySet().models(CourseOffering).filter(text='Babbling')
        self.assertEqual(len(res), 0)
        res = SearchQuerySet().models(CourseOffering).filter(text='Something')
        self.assertEqual(len(res), 1)

        # but we do update Pages in real time
        res = SearchQuerySet().models(Page).filter(text='fernwhizzles')
        self.assertEqual(len(res), 0)

        # create a page
        p = Page(offering=self.offering, label='SomePage', can_read='ALL', can_write='STAF')
        p.save()
        pv = PageVersion(page=p, title='Some Page', wikitext='This is a page about fernwhizzles.', editor=self.instructor)
        pv.save()
        res = SearchQuerySet().models(Page).filter(text='fernwhizzles')
        self.assertEqual(len(res), 1)

        # update a page
        pv = PageVersion(page=p, title='Some Page', wikitext='This is a page about bobdazzles.', editor=self.instructor)
        pv.save()
        res = SearchQuerySet().models(Page).filter(text='fernwhizzles')
        self.assertEqual(len(res), 0)
        res = SearchQuerySet().models(Page).filter(text='bobdazzles')
        self.assertEqual(len(res), 1)
