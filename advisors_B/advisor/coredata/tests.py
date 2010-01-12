from django.test import TestCase
from coredata.models import *

from django.db.models import *
from django.db import IntegrityError
from datetime import date

def create_semester():
    s = Semester(name="1077", start=date(2007,9,4), end=date(2007,12,3))
    s.save()
    return s

def create_offering():
    s = create_semester()
    c = CourseOffering(subject="CMPT", number="120", section="D100", semester=s, component="LEC",
                graded=True, crse_id=11111, class_nbr=22222, campus='BRNBY',
                enrl_cap=100, enrl_tot=99, wait_tot=2)
    c.save()
    return s, c


class CoredataTest(TestCase):
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
            self.assertEqual(len(w), 1)
            # check all week.monday are really Monday
            for w in s.semesterweek_set.all():
                self.assertEqual(w.monday.weekday(), 0)

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
        people = Person.objects.all()
        # check sorting
        self.assertEquals(p1, people[0])
        self.assertEquals(p2, people[1])
        self.assertEquals(p3, people[2])
        
        # uniqueness checking for emplid and userid
        px = Person(emplid=210012345, userid="test4")
        self.assertRaises(IntegrityError, px.save)
        px = Person(emplid=210012348, userid="test1")
        self.assertRaises(IntegrityError, px.save)
        
    def test_semester(self):
        """
        Create and test a semester object
        """
        s = create_semester()
        wk = SemesterWeek(semester=s, week=1, monday=date(2007,9,3))
        wk.save()
        
        self.assertEquals(s.label(), "Fall 2007")
        
        s2 = Semester(name="1077", start=date(2007,9,4), end=date(2007,12,3))
        self.assertRaises(IntegrityError, s2.save)
        

    def test_course_offering(self):
        """
        Create and test a course offering
        """
        s, c = create_offering()
        
        # should have a get_absolute_url
        url = c.get_absolute_url()
        self.assertEquals(url, str(url))
        self.assertEquals(url[0], '/')

        # check uniqueness criteria
        c2 = CourseOffering(subject="CMPT", number="120", section="D100", semester=s, component="LAB",
                graded=True, crse_id=11112, class_nbr=22223, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        self.assertRaises(IntegrityError, c2.save)

        c2 = CourseOffering(subject="CMPT", number="121", section="D100", semester=s, component="LAB",
                graded=True, crse_id=11111, class_nbr=22223, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        self.assertRaises(IntegrityError, c2.save)

        c2 = CourseOffering(subject="MACM", number="121", section="D102", semester=s, component="LAB",
                graded=True, crse_id=11112, class_nbr=22222, campus='SURRY',
                enrl_cap=101, enrl_tot=100, wait_tot=3)
        self.assertRaises(IntegrityError, c2.save)

