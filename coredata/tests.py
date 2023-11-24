from django.test import TestCase
from haystack.query import SearchQuerySet

from coredata.models import CourseOffering, Semester, Person, SemesterWeek, \
                            Member, Role, Unit, EnrolmentHistory, ROLE_CHOICES

from django.urls import reverse

from courselib.search import haystack_update_index, haystack_clear_index, haystack_rebuild_index
from courselib.testing import basic_page_tests, validate_content, Client, \
                              TEST_COURSE_SLUG, TEST_ROLE_EXPIRY

from django.db import IntegrityError
from datetime import date, datetime, timedelta
import pytz, json


def create_semesters():
    semester_1124 = Semester(name="1124", start=date(2012,4,4), end=date(2012,9,3))
    semester_1124.save()
    semester_1127 = Semester(name="1127", start=date(2012,9,4), end=date(2012,12,3))
    semester_1127.save()
    semester_1131 = Semester(name="1131", start=date(2013,1,4), end=date(2013,4,3))
    semester_1131.save()
    semester_1134 = Semester(name="1134", start=date(2013,4,4), end=date(2013,9,3))
    semester_1134.save()
    semester_1137 = Semester(name="1137", start=date(2013,9,4), end=date(2013,12,3))
    semester_1137.save()
    semester_1141 = Semester(name="1141", start=date(2014,1,4), end=date(2014,4,3))
    semester_1141.save()
    semester_1144 = Semester(name="1144", start=date(2014,4,4), end=date(2014,9,3))
    semester_1144.save()
    semester_1147 = Semester(name="1147", start=date(2014,9,4), end=date(2014,12,3))
    semester_1147.save()
    semester_1151 = Semester(name="1151", start=date(2015,1,4), end=date(2015,4,3))
    semester_1151.save()
    semester_1154 = Semester(name="1154", start=date(2015,4,4), end=date(2015,9,3))
    semester_1154.save()
    semester_1157 = Semester(name="1157", start=date(2015,9,4), end=date(2015,12,3))
    semester_1157.save()
    semester_1161 = Semester(name="1161", start=date(2016,1,4), end=date(2016,4,3))
    semester_1161.save()
    semester_1164 = Semester(name="1164", start=date(2016,4,4), end=date(2016,9,3))
    semester_1164.save()
    semester_1167 = Semester(name="1167", start=date(2016,9,4), end=date(2016,12,3))
    semester_1167.save()

def create_unit():
    unit = Unit(label="UNIV", name="Testington University")
    unit.save()
    return unit

def create_greg(unit):
    baker = Person(emplid="123456789", userid="ggbaker", first_name="Greg", last_name="Baker")
    baker.config['privacy_date'] = date(2008,9,9)
    baker.config['privacy_version'] = 1
    baker.config['privacy_da_date'] = date(2008, 9, 9)
    baker.config['privacy_da_version'] = 1
    baker.save()
    for role_tuple in ROLE_CHOICES:
        role = Role(person=baker, role=role_tuple[0], unit=unit, expiry=date.today())
        role.save()
    return baker

def create_semester():
    this_yr = date.today().year
    s = Semester(name="1077", start=date(this_yr,9,4), end=date(this_yr,12,3))
    s.save()
    return s

def create_offering():
    s = create_semester()
    c = CourseOffering(subject="CMPT", number="120", section="D100", semester=s, component="LEC",
                graded=True, crse_id=11111, class_nbr=22222, campus='BRNBY', title="Computer Stuff",
                enrl_cap=100, enrl_tot=99, wait_tot=2)
    c.save()
    return s, c


class CoredataTest(TestCase):

    def setUp(self):
        unit = create_unit()
        person = create_greg(unit)
        create_semesters()

    def test_person(self):
        """
        Basics of Person objects.
        """
        # create some people to test with
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p2 = Person(emplid=210012346, userid="test2",
                last_name="Lname", first_name="Zname", pref_first_name="Gn", middle_name="M")
        p3 = Person(emplid=210012347, userid="test3",
                last_name="Zname", first_name="Fname", pref_first_name="Gn", middle_name="M")
        p3.save()
        p1.save()
        p2.save()
        
        self.assertEqual(str(p1), "Lname, Fname")
        self.assertEqual(p1.name(), "Fname Lname")
        self.assertEqual(p1.email(), "test1@sfu.ca")
        people = Person.objects.filter(userid__startswith="test")
        # check sorting
        self.assertEqual(p1, people[0])
        self.assertEqual(p2, people[1])
        self.assertEqual(p3, people[2])
        
        # uniqueness checking for emplid and userid
        px = Person(emplid=210012345, userid="test4")
        self.assertRaises(IntegrityError, px.save)

    def test_person_2(self):
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p1.save()
        px = Person(emplid=210012348, userid="test1")
        self.assertRaises(IntegrityError, px.save)
    
    def _test_due_date(self, s, dt, wk, wkday, reverse=None):
        """
        Test for semester.week_weekday and semester.duedate
        """
        wk0, wkday0 = s.week_weekday(dt)
        self.assertEqual((wk,wkday), (wk0,wkday0))
        due = s.duedate(wk, wkday, dt)
        if not reverse:
            reverse = dt

        self.assertEqual(reverse, due)
        
    
    def test_semester(self):
        """
        Create and test a semester object
        """
        s = create_semester()
        wk = SemesterWeek(semester=s, week=1, monday=date(2007,9,3))
        wk.save()
        wk = SemesterWeek(semester=s, week=5, monday=date(2007,10,8)) # pretend there is a Oct 1-5 break
        wk.save()
        
        self.assertEqual(s.label(), "Fall 2007")
        self.assertEqual(str(wk), "1077 week 5")

        # test semester arithmetic
        s = Semester.objects.get(name='1131')
        self.assertEqual(s.previous_semester().name, '1127')
        self.assertEqual(s.offset(1).name, '1134')
        self.assertEqual(s.offset(-1).name, '1127')
        self.assertEqual(s.offset(2).name, '1137')
        self.assertEqual(s.offset(-2).name, '1124')
        self.assertEqual(s - s.offset(-2), 2)
        self.assertEqual(s.offset(-2) - s, -2)

        self.assertEqual(s.offset_name(1), '1134')
        self.assertEqual(s.offset_name(-1), '1127')
        self.assertEqual(s.offset_name(2), '1137')
        self.assertEqual(s.offset_name(-2), '1124')
        self.assertEqual(s.offset_name(3), '1141')
        self.assertEqual(s.offset_name(-3), '1121')
        self.assertEqual(s.offset_name(4), '1144')
        self.assertEqual(s.offset_name(-4), '1117')

        s2 = Semester(name="1077", start=date(2007,9,4), end=date(2007,12,3))
        self.assertRaises(IntegrityError, s2.save)
        
    def test_semester_2(self):
        s = create_semester()
        wk = SemesterWeek(semester=s, week=1, monday=date(2007,9,3))
        wk.save()
        wk = SemesterWeek(semester=s, week=5, monday=date(2007,10,8)) # pretend there is a Oct 1-5 break
        wk.save()

        # test due date calculations: convert date to week-of-semester and weekday (and back)
        tz = pytz.timezone('America/Vancouver')
        
        dt = datetime(2007, 9, 19, 23, 59, 59)
        self._test_due_date(s, dt, 3, 2)
        
        dt = datetime(2007, 11, 16, 16, 0, 0, tzinfo=tz) # timezone change between this and previous SemesterWeek
        self._test_due_date(s, dt, 10, 4)

        dt = datetime(2007, 11, 4, tzinfo=tz) # timezone change between this and previous Monday
        self._test_due_date(s, dt, 8, 6)

        dt = datetime(2007, 10, 10, tzinfo=tz) # right after a break
        self._test_due_date(s, dt, 5, 2)
        
        dt = datetime(2007, 10, 3, tzinfo=tz) # during a break
        # shouldn't be inverse function here: duedate always returns an in-semester date
        self._test_due_date(s, dt, 5, 2, reverse=datetime(2007,10,10, tzinfo=tz))

        wk, wkday = s.week_weekday(date(2007, 10, 3))
        self.assertEqual(wk, 5)
        self.assertEqual(wkday, 2)

        # check weird special-case for before-the-start dates
        self.assertEqual(s.week_weekday(date(2007, 9, 2)), (1, 0))

        
        

    def test_course_offering(self):
        """
        Create and test a course offering
        """
        s, c = create_offering()
        
        # should have a get_absolute_url
        url = c.get_absolute_url()
        self.assertEqual(url, str(url))
        self.assertEqual(url[0], '/')
        self.assertEqual(str(c), "CMPT 120 D100 (Fall 2007)")
        self.assertEqual(c.name(), "CMPT 120 D1")

        # check uniqueness criteria
        c2 = CourseOffering(subject="CMPT", number="120", section="D100", semester=s, component="LAB",
                graded=True, crse_id=11112, class_nbr=22223, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        # south doesn't seem to create the constraints in SQLite for testing
        #self.assertRaises(IntegrityError, c2.save)

        c2 = CourseOffering(subject="CMPT", number="121", section="D100", semester=s, component="LAB",
                graded=True, crse_id=11111, class_nbr=22223, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        # south doesn't seem to create the constraints in SQLite for testing
        #self.assertRaises(IntegrityError, c2.save)

        c2 = CourseOffering(subject="MACM", number="121", section="D102", semester=s, component="LAB",
                graded=True, crse_id=11112, class_nbr=22222, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        # south doesn't seem to create the constraints in SQLite for testing
        #self.assertRaises(IntegrityError, c2.save)

        # test some course memberships
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p1.save()
        m = Member(person=p1, offering=c, role="INST", credits=0, career="NONS", added_reason="AUTO")
        m.save()
        
        self.assertEqual( str(list(c.instructors())), "[<Person: Lname, Fname>]")
        self.assertEqual( str(list(c.tas())), "[]")
        self.assertEqual( c.student_count(), 0)

        m.role = "TA"
        m.save()
        self.assertEqual( str(list(c.instructors())), "[]")
        self.assertEqual( str(list(c.tas())), "[<Person: Lname, Fname>]")
        self.assertEqual( c.student_count(), 0)

        m.role = "STUD"
        m.save()
        self.assertEqual( str(list(c.instructors())), "[]")
        self.assertEqual( str(list(c.tas())), "[]")
        self.assertEqual( c.student_count(), 1)
        
        self.assertEqual( str(m), "test1 (210012345) in CMPT 120 D100 (Fall 2007)")

    def test_roles(self):
        # create person an give sysadmin role
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p1.save()
        
        unit = Unit.objects.get(label="UNIV")
        r = Role(person=p1, role="SYSA", unit=unit, expiry=TEST_ROLE_EXPIRY)
        r.save()
        self.assertEqual( str(r), "Lname, Fname (System Administrator, UNIV)")

        # check the front end
        client = Client()
        client.login_user("test1")

        url = reverse('sysadmin:role_list')
        response = basic_page_tests(self, client, url)
        self.assertContains(response, 'Lname, Fname</a></td>\n  <td>System Administrator</td>')

        # add a new role with the front end
        oldcount = Role.objects.filter(role='FAC').count()
        url = reverse('sysadmin:new_role')
        response = basic_page_tests(self, client, url)
        
        response = client.post(url, {'person':'33333333', 'role':'FAC', 'unit': 2})
        self.assertEqual(response.status_code, 200)
        validate_content(self, response.content, url)
        self.assertTrue(b"could not import DB2 module" in response.content
                        or b"could not connect to reporting database" in response.content
                        or b"Could not find this emplid." in response.content
                        or b"Reporting database access has been disabled" in response.content
                        or b"Could not communicate with reporting database" in response.content)

        response = client.post(url, {'person':p1.emplid, 'role':'FAC', 'unit':unit.id, 'expiry': str(TEST_ROLE_EXPIRY)})
        self.assertEqual(response.status_code, 302)
        
        # make sure the role is now there
        self.assertEqual( Role.objects.filter(role='FAC').count(), oldcount+1)

    def test_role_access(self):
        r = Role.objects.filter(role='SYSA')[0]
        p = r.person
        p.config['privacy_signed'] = True
        p.config['privacy_da_signed'] = True
        p.save()

        client = Client()
        client.login_user(r.person.userid)
        url = reverse('sysadmin:new_role')

        # test data role expires in the future: should allow.
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)

        # expire the role: should now forbid.
        r.expiry = date.today() - timedelta(days=2)
        r.save()
        resp = client.get(url)
        self.assertEqual(resp.status_code, 403)


class SlowCoredataTest(TestCase):
    fixtures = ['basedata', 'coredata']
    
    def test_course_browser(self):
        client = Client()

        s, c = create_offering()
        
        # the main search/filter page
        url = reverse('browse:browse_courses')
        response = basic_page_tests(self, client, url)

        # AJAX request for table data
        url += '?tabledata=yes&data_type=json&iDisplayStart=0&iDisplayLength=10&iSortingCols=0'
        response = client.get(url)
        data = json.loads(response.content.decode('utf8'))
        self.assertEqual(len(data['aaData']), 10)

        # courseoffering detail page
        url = reverse('browse:browse_courses_info', kwargs={'course_slug': TEST_COURSE_SLUG})
        response = basic_page_tests(self, client, url)
    
    def disabled_test_ajax(self):
        # disabled because haystack + tests aren't behaving well
        client = Client()
        haystack_update_index() # make sure we have the same data in DB and haystack

        # test person autocomplete
        client.login_user("dzhao")
        p = Person.objects.get(userid='ggbaker')
        url = reverse('data:student_search')
        response = client.get(url, {'term': 'ggba'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        # should find this person
        data = json.loads(response.content.decode('utf8'))
        emplids = [str(d['value']) for d in data]
        self.assertIn(str(p.emplid), emplids)


class EnrolmentHistoryTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        offerings = CourseOffering.objects.all()
        o1 = offerings[0]
        o2 = offerings[1]
        self.o1 = o1
        self.o2 = o2

        o1.enrl_cap = 10
        o1.enrl_tot = 15
        o1.wait_tot = 2
        EnrolmentHistory.from_offering(o1, date='2017-01-01')
        EnrolmentHistory.from_offering(o1, date='2017-01-02')
        o1.enrl_cap = 13
        EnrolmentHistory.from_offering(o1, date='2017-01-03')
        EnrolmentHistory.from_offering(o1, date='2017-01-05')
        o1.wait_tot = 3
        EnrolmentHistory.from_offering(o1, date='2017-01-07')

        o2.enrl_cap = 20
        o2.enrl_tot = 25
        o2.wait_tot = 7
        EnrolmentHistory.from_offering(o2, date='2017-01-01')
        EnrolmentHistory.from_offering(o2, date='2017-01-02')
        EnrolmentHistory.from_offering(o2, date='2017-01-03')
        EnrolmentHistory.from_offering(o2, date='2017-01-04')
        o2.enrl_tot = 30
        EnrolmentHistory.from_offering(o2, date='2017-01-05')
        EnrolmentHistory.from_offering(o2, date='2017-01-06')

    def test_dedupe(self):
        EnrolmentHistory.deduplicate()
        eh1 = EnrolmentHistory.objects.filter(offering=self.o1).order_by('date')
        self.assertEqual(eh1.count(), 3)
        self.assertEqual(eh1[0].date, date(2017, 1, 1))
        self.assertEqual(eh1[0].enrl_vals, (10, 15, 2))
        self.assertEqual(eh1[1].date, date(2017, 1, 3))
        self.assertEqual(eh1[1].enrl_vals, (13, 15, 2))
        self.assertEqual(eh1[2].date, date(2017, 1, 7))
        self.assertEqual(eh1[2].enrl_vals, (13, 15, 3))

        eh2 = EnrolmentHistory.objects.filter(offering=self.o2).order_by('date')
        self.assertEqual(eh2.count(), 2)
        self.assertEqual(eh2[0].date, date(2017, 1, 1))
        self.assertEqual(eh2[0].enrl_vals, (20, 25, 7))
        self.assertEqual(eh2[1].date, date(2017, 1, 5))
        self.assertEqual(eh2[1].enrl_vals, (20, 30, 7))


class SearchTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_search_updates(self):
        """
        Make sure indexing in Haystack is working as we expect.
        """
        fname = 'TestStudentUnusualName'
        s, c = create_offering()
        # make sure the test semester is reasonably current
        today = date.today()
        s.start = today - timedelta(days=100)
        s.end = today + timedelta(days=100)
        s.save()

        # clear the search index and query: we shouldn't find anything.
        haystack_clear_index()
        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 0)

        # add something searchable and query: we don't expect it to appear in real-time
        p = Person(last_name='Test', first_name=fname, userid='0aaa99999', emplid=123456)
        p.save()
        m = Member(person=p, offering=c, role='STUD')
        m.save()

        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 0)

        # ... but after update_index.we do.
        haystack_update_index()
        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 1)

        # same for removing from the index.
        m.role = 'DROP'
        m.save()
        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 1)

        # update_index doesn't detect a data change that excludes the object from the index_queryset
        haystack_update_index()
        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 1)

        # but rebuild_index will fix that up.
        haystack_rebuild_index()
        results = SearchQuerySet().models(Member).filter(text__fuzzy=fname)
        self.assertEqual(results.count(), 0)


class DependencyTest(TestCase):
    """
    Tests of dependent libraries, where there have been problems
    """
    def _flag_filter(self, filters):
        q = CourseOffering.objects
        for f in filters:
            q = q.filter(flags=f)
        return set(q)

    def test_bitfield(self):
        s, c1 = create_offering()
        c2 = CourseOffering(subject="CMPT", number="121", section="D100", semester=s, component="LEC",
                           graded=True, crse_id=11112, class_nbr=22223, campus='BRNBY', title="Other Stuff",
                           enrl_cap=100, enrl_tot=99, wait_tot=2)
        c2.save()

        c1.flags = CourseOffering.flags.quant
        c1.save()
        self.assertEqual(self._flag_filter([CourseOffering.flags.quant, CourseOffering.flags.bhum]), set())
        self.assertEqual(self._flag_filter([CourseOffering.flags.quant]), {c1})
        self.assertEqual(self._flag_filter([~CourseOffering.flags.quant]), {c2})
        self.assertEqual(self._flag_filter([~CourseOffering.flags.bhum]), {c1, c2})

        c1.flags = 0
        c1.save()
        self.assertEqual(self._flag_filter([CourseOffering.flags.quant]), set())
        self.assertEqual(self._flag_filter([~CourseOffering.flags.quant]), {c1, c2})

    def test_jsonfield(self):
        from grades.models import CalNumericActivity
        s, c = create_offering()
        a = CalNumericActivity(offering=c, name="Test", short_name="Test", max_grade=10, position=1)
        a.config = {'showstats': True}
        a.save()

        # https://github.com/bradjasper/django-jsonfield/issues/106
        a = CalNumericActivity.objects.get(slug='test')
        self.assertIsInstance(a.config, dict)

    def test_cache_utils(self):
        from cache_utils.decorators import cached
        @cached(36000)
        def f(s):
            return len(s)

        n = 100
        self.assertEqual(f('乐' * n), n)