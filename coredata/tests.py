from django.test import TestCase
from coredata.models import *

from django.core.urlresolvers import reverse
from django.test.client import Client
from courselib.testing import *
from settings import CAS_SERVER_URL

from django.db.models import *
from django.db import IntegrityError
from datetime import date, datetime
import pytz

def create_semester():
    s = Semester(name="1077", start=date(2007,9,4), end=date(2007,12,3))
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
    fixtures = ['test_data']
    def setUp(self):
        pass
    
    def test_test_data(self):
        """
        Make sure we have some decent test data in place.
        """
        sems = Semester.objects.all()
        self.assertTrue(len( sems ) >= 4)
        for s in sems:
            # make sure that every semester has a week #1
            w = s.semesterweek_set.filter(week=1)
            self.assertEqual(w.count(), 1, "Semester %s doesn't have a SemesterWeek for week 1" % (s))
            # check all week.monday are really Monday
            for w in s.semesterweek_set.all():
                self.assertEqual(w.monday.weekday(), 0, "Semester %s's SemesterWeek doesn't start on a Monday" % (s))

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
        
        self.assertEquals(str(p1), "Lname, Fname")
        self.assertEquals(p1.name(), "Fname Lname")
        self.assertEquals(p1.email(), "test1@sfu.ca")
        people = Person.objects.filter(userid__startswith="test")
        # check sorting
        self.assertEquals(p1, people[0])
        self.assertEquals(p2, people[1])
        self.assertEquals(p3, people[2])
        
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
        
        self.assertEquals(s.label(), "Fall 2007")
        self.assertEquals(str(wk), "1077 week 5")

        # test semester arithmetic
        s = Semester.objects.get(name='1121')
        self.assertEqual(s.previous_semester().name, '1117')
        self.assertEqual(s.offset(1).name, '1124')
        self.assertEqual(s.offset(-1).name, '1117')
        self.assertEqual(s.offset(2).name, '1127')
        self.assertEqual(s.offset(-2).name, '1114')
        self.assertEqual(s - s.offset(-2), 2)
        self.assertEqual(s.offset(-2) - s, -2)
        
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

        self.assertRaises(ValueError, s.week_weekday, date(2007, 9, 2))
        
        
        

    def test_course_offering(self):
        """
        Create and test a course offering
        """
        s, c = create_offering()
        
        # should have a get_absolute_url
        url = c.get_absolute_url()
        self.assertEquals(url, str(url))
        self.assertEquals(url[0], '/')
        self.assertEquals(str(c), "CMPT 120 D100 (Fall 2007)")
        self.assertEquals(c.name(), "CMPT 120 D1")

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
        r = Role(person=p1, role="SYSA", unit=unit)
        r.save()
        self.assertEqual( str(r), "Lname, Fname (System Administrator, UNIV)")

        # check the front end
        client = Client()
        client.login(ticket="test1", service=CAS_SERVER_URL)

        url = reverse('coredata.views.role_list')
        response = basic_page_tests(self, client, url)
        self.assertContains(response, 'Lname, Fname</a></td><td>System Administrator</td>')

        # add a new role with the front end
        oldcount = Role.objects.filter(role='FAC').count()
        url = reverse('coredata.views.new_role')
        response = basic_page_tests(self, client, url)
        
        response = client.post(url, {'person':'33333333', 'role':'FAC'})
        self.assertEquals(response.status_code, 200)
        validate_content(self, response.content, url)
        #self.assertContains(response, "Could not find this emplid.")
        #self.assertContains(response, "could not connect to reporting database")
        self.assertTrue("could not connect to reporting database" in response.content or "Could not find this emplid." in response.content)

        response = client.post(url, {'person':p1.emplid, 'role':'FAC', 'unit':unit.id})
        self.assertEquals(response.status_code, 302)
        
        # make sure the role is now there
        self.assertEquals( Role.objects.filter(role='FAC').count(), oldcount+1)