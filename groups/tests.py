from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL

from coredata.tests import create_offering
from coredata.models import *
from grades.models import *
from courselib.testing import *
from groups.models import *
from django.core.urlresolvers import reverse

import re

class GroupTest(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        pass

    def test_group_student(self):
        """
        Check out group pages for student: go through the whole group-creation process from the student side.
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="URLS", offering=c, position=3, max_grade=20, group=True)
        a.save()
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        
        userid1 = "0kvm"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        for u in [userid1, userid2, userid3]:
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
        
        
        

