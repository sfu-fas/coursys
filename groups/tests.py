from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL

from coredata.tests import create_offering
from coredata.models import *
from grades.models import *
from courselib.testing import *
from groups.models import *
from django.core.urlresolvers import reverse
from django.db import IntegrityError

import re
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from grades.models import Activity
from django.db.models import Q

class GroupTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_group_models(self):
        """
        Test the backend for groups
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="URLS", offering=c, position=3, max_grade=20, group=True)
        a.save()
        a1 = a
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        a2 = a
        
        userid1 = "0kvm"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        userid4 = "0aaa2"
        for u in [userid1, userid2, userid3, userid4]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        
        # basics
        m = Member.objects.get(person__userid=userid1, offering=c)
        g = Group(name="Test Group", manager=m, courseoffering=c)
        g.save()
        self.assertEqual(g.slug, 'g-test-group')
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        m = Member.objects.get(person__userid=userid2, offering=c)
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        
        gs = Group.objects.filter(courseoffering=c)
        self.assertEqual(len(gs), 1)
        g = gs[0]
        self.assertEqual(set([gm.student.person.userid for gm in g.groupmember_set.all()]), set([userid1,userid2]))

        # check uniqueness of activity + member        
        m = Member.objects.get(person__userid=userid3, offering=c)
        g2 = Group(name="Other Group", manager=m, courseoffering=c)
        g2.save()
        gm = GroupMember(group=g2, student=m, confirmed=True, activity=a1)
        gm.save()
        
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        self.assertRaises(IntegrityError, gm.save)
        
        # uniqueness of group name
        g3 = Group(name="Other Group", manager=m, courseoffering=c)
        self.assertRaises(IntegrityError, g3.save)
        
        # finding all activities this group covers
        members = GroupMember.objects.filter(group=g)
        all_act = all_activities(members)
        self.assertEqual(set(a.slug for a in all_act), set([a1.slug]))

        # add a member for assignment 2 and check again
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()
        members = GroupMember.objects.filter(group=g)
        all_act = all_activities(members)
        self.assertEqual(set(a.slug for a in all_act), set([a1.slug, a2.slug]))

    def test_invite_members(self):
        self.slug='1101-cmpt-165-d100'
        c = CourseOffering.objects.get(slug = self.slug)
        
        p1 = Person(userid='0aaa0')
        p1.save()
        p2 = Person(userid='0aaa1')
        p2.save()
        Memb0=Member(person=p1,offering=c)
        Memb0.save()
        Memb1=Member(person=p2,offering=c)
        Memb1.save()
        g = Group(name = 'A1', manager = Memb0, courseoffering=c)
        g.save()
        
        
        act = Activity.objects.filter(Q(status='RLS') | Q(status='URLS'), offering = course, group=True)
        GMemb1=GroupMember(group=g,activity=act,student=Memb1,confirmed=False)
        GMemb1.save()
        
        gm=all_GroupMember_filter(group=g)
        self.assertEqual(len(gm), 1) 

    def test_group_student(self):
        """
        Check out group pages for student: go through the whole group-creation process from the student side.
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="URLS", offering=c, position=3, max_grade=20, group=True)
        a.save()
        a1 = a
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        
        userid1 = "0kvm"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        userid4 = "0aaa2"
        for u in [userid1, userid2, userid3, userid4]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        
        client = Client()
        client.login(ticket=userid1, service=CAS_SERVER_URL)
        
        # group management screen
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "You don't belong to any groups")
        url = reverse('groups.views.create', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="%s"'%(url))
        
        # group creation form
        response = basic_page_tests(self, client, url)

        # submit group create
        url = reverse('groups.views.submit', kwargs={'course_slug': c.slug})
        response = client.post(url, {"GroupName": "Test Group", "a1-selected": True, "a2-selected": False})
        self.assertEquals(response.status_code, 302)
        
        gs =  Group.objects.filter(courseoffering=c)
        self.assertEquals(len(gs), 1)
        self.assertEquals(gs[0].name, "Test Group")
        self.assertEquals(gs[0].manager.person.userid, userid1)

        gms = GroupMember.objects.filter(group__courseoffering=c)
        self.assertEquals(len(gms), 1)
        self.assertEquals(gms[0].student.person.userid, userid1)
        self.assertEquals(gms[0].confirmed, True)
        
        # member invite form
        url = reverse('groups.views.invite', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = basic_page_tests(self, client, url)
        
        # submit invite form: invite userid2 and userid3
        response = client.post(url, {"name": userid2})
        response = client.post(url, {"name": userid3})
        self.assertEquals(response.status_code, 302)
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid__in=[userid2,userid3])
        self.assertEquals(len(gms), 2)
        self.assertEquals(gms[0].confirmed, False)
        self.assertEquals(gms[1].confirmed, False)
        
        # log in as userid2 and confirm
        client.login(ticket=userid2, service=CAS_SERVER_URL)
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "Kim Moore, 0kvm")
        self.assertContains(response, "A Student, 0aaa0 (unconfirmed)")
        
        url = reverse('groups.views.join', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = client.get(url)
        self.assertEquals(response.status_code, 302)
        
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid=userid2)
        self.assertEquals(len(gms), 1)
        self.assertEquals(gms[0].confirmed, True)
        
        # log in as userid3 and reject
        client.login(ticket=userid3, service=CAS_SERVER_URL)
        url = reverse('groups.views.reject', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = client.get(url)
        self.assertEquals(response.status_code, 302)
        
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid=userid3)
        self.assertEquals(len(gms), 0)

        # inviting userid4 shouldn't work if already in a group
        m = Member.objects.get(person__userid=userid4, offering=c)
        g = Group(name="Other Group", manager=m, courseoffering=c)
        g.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        
        client.login(ticket=userid1, service=CAS_SERVER_URL)
        url = reverse('groups.views.invite', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = client.post(url, {"name": userid4})
        
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid=userid4)
        self.assertEqual(len(gms), 1)
        self.assertEqual(gms[0].group.slug, 'g-other-group')


    def test_group_staff(self):
        """
        Check out group pages for an instructor: go through the group-creation process from the instructor side.
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="URLS", offering=c, position=3, max_grade=20, group=True)
        a.save()
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        
        userid1 = "0kvm"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        userid4 = "ggbaker"
        for u in [userid1, userid2, userid3, userid4]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        m.role="INST"
        m.save()
        
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        # group management screen
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "There are currently no groups in this course")
        url = reverse('groups.views.create', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="%s"'%(url))
        
        # group creation form
        response = basic_page_tests(self, client, url)

        # submit group create
        url = reverse('groups.views.submit', kwargs={'course_slug': c.slug})
        response = client.post(url, {"GroupName": "Test Group", "a1-selected": True, "a2-selected": False, 
                '0kvm-selected': False, '0aaa0-selected': True, '0aaa1-selected': True})
        self.assertEquals(response.status_code, 302)

        gs =  Group.objects.filter(courseoffering=c)
        self.assertEquals(len(gs), 1)
        self.assertEquals(gs[0].name, "Test Group")

        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0])
        self.assertEquals(len(gms), 2)
        self.assertEquals(gms[0].confirmed, True)
        self.assertEquals(gms[1].confirmed, True)
        self.assertEquals(set(gm.student.person.userid for gm in gms), set([userid2,userid3]))
        
        # check group management screen again
        url = reverse('groups.views.groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assert_( re.search(r"Test Group\s+\(for\s+Assignment 1\)", response.content) )
        
        
        

