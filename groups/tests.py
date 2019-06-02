from django.conf import settings
CAS_SERVER_URL = settings.CAS_SERVER_URL

from coredata.tests import create_offering
from courselib.testing import *
from groups.models import *
from submission.models import GroupSubmission


class GroupTest(TestCase):
    fixtures = ['basedata', 'coredata', 'grades']

    def setUp(self):
        self.c_slug = '1114-cmpt-120-d100'

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
        
        userid1 = "0aaa4"
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
        # south doesn't seem to create the constraints in SQLite for testing
        #self.assertRaises(IntegrityError, gm.save)
        
        # uniqueness of group name
        g3 = Group(name="Other Group", manager=m, courseoffering=c)
        # south doesn't seem to create the constraints in SQLite for testing
        #self.assertRaises(IntegrityError, g3.save)
        
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
        
        # check student-editable tests
        
        # test dates
        m = Member.objects.get(offering=c, person__userid="0aaa0")
        gm = GroupMember.objects.get(group=g, student=m, activity=a1)

        a1.due_date = datetime.datetime.now() - datetime.timedelta(days=1) # yesterday
        a1.save()
        self.assertTrue("passed" in gm.student_editable("0aaa0"))

        a1.due_date = datetime.datetime.now() + datetime.timedelta(days=1) # tomorrow
        a1.save()
        gm = GroupMember.objects.get(group=g, student=m, activity=a1)
        self.assertEqual(gm.student_editable("0aaa0"), '')

        # not member for this activity
        self.assertTrue("not a member" in gm.student_editable("0aaa1"))
        
        # already graded
        gr = NumericGrade(activity=a1, member=m, value=1, flag="GRAD")
        gr.save(entered_by='ggbaker')
        self.assertTrue("grade" in gm.student_editable("0aaa0"))
        gr.flag="NOGR"
        gr.save(entered_by='ggbaker')
        self.assertEqual(gm.student_editable("0aaa0"), '')
        
        # submission made
        s = GroupSubmission(group=g, creator=m, activity=a1)
        s.save()
        self.assertTrue("submission" in gm.student_editable("0aaa0"))
        

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
        
        userid1 = "0aaa6"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        userid4 = "0aaa2"
        for u in [userid1, userid2, userid3, userid4]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        
        client = Client()
        client.login_user(userid1)
        
        # group management screen
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "You don't belong to any group")
        url = reverse('offering:groups:create', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="%s"'%(url))
        
        # group creation form
        response = basic_page_tests(self, client, url)

        # submit group create
        url = reverse('offering:groups:submit', kwargs={'course_slug': c.slug})
        response = client.post(url, {"GroupName": "Test Group", "a1-selected": True, "a2-selected": False})
        self.assertEqual(response.status_code, 302)
        
        gs =  Group.objects.filter(courseoffering=c)
        self.assertEqual(len(gs), 1)
        self.assertEqual(gs[0].name, "Test Group")
        self.assertEqual(gs[0].manager.person.userid, userid1)

        gms = GroupMember.objects.filter(group__courseoffering=c)
        self.assertEqual(len(gms), 1)
        self.assertEqual(gms[0].student.person.userid, userid1)
        self.assertEqual(gms[0].confirmed, True)
        
        # member invite form
        url = reverse('offering:groups:invite', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = basic_page_tests(self, client, url)
        
        # submit invite form: invite userid2 and userid3
        response = client.post(url, {"name": userid2})
        response = client.post(url, {"name": userid3})
        self.assertEqual(response.status_code, 302)
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid__in=[userid2,userid3])
        self.assertEqual(len(gms), 2)
        self.assertEqual(gms[0].confirmed, False)
        self.assertEqual(gms[1].confirmed, False)
        
        # log in as userid2 and confirm
        client.login_user(userid2)
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, ", "+userid1)
        self.assertContains(response, ", "+userid2+" (unconfirmed)")
        
        url = reverse('offering:groups:join', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid=userid2)
        self.assertEqual(len(gms), 1)
        self.assertEqual(gms[0].confirmed, True)
        
        # log in as userid3 and reject
        client.login_user(userid3)
        url = reverse('offering:groups:reject', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        
        gms = GroupMember.objects.filter(group__courseoffering=c, student__person__userid=userid3)
        self.assertEqual(len(gms), 0)

        # inviting userid4 shouldn't work if already in a group
        m = Member.objects.get(person__userid=userid4, offering=c)
        g = Group(name="Other Group", manager=m, courseoffering=c)
        g.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        
        client.login_user(userid1)
        url = reverse('offering:groups:invite', kwargs={'course_slug': c.slug, 'group_slug':'g-test-group'})
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
        
        userid1 = "0aaa6"
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
        client.login_user("ggbaker")
        
        # group management screen
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "There are currently no groups in this course")
        url = reverse('offering:groups:create', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="%s"'%(url))
        
        # group creation form
        response = basic_page_tests(self, client, url)

        # submit group create
        url = reverse('offering:groups:submit', kwargs={'course_slug': c.slug})
        response = client.post(url, {"GroupName": "Test Group", "a1-selected": True, "a2-selected": False, 
                '0aaa6-selected': False, '0aaa0-selected': True, '0aaa1-selected': True})
        self.assertEqual(response.status_code, 302)

        gs =  Group.objects.filter(courseoffering=c)
        self.assertEqual(len(gs), 1)
        self.assertEqual(gs[0].name, "Test Group")
        self.assertEqual(gs[0].slug, "g-test-group")

        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0])
        self.assertEqual(len(gms), 2)
        self.assertEqual(gms[0].confirmed, True)
        self.assertEqual(gms[1].confirmed, True)
        self.assertEqual(set(gm.student.person.userid for gm in gms), set([userid2,userid3]))
        
        # check group management screen again
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)

        # add membership form
        url = reverse('offering:groups:assign_student', kwargs={'course_slug': c.slug, 'group_slug': "g-test-group"})
        response = basic_page_tests(self, client, url)
        
        # submit add membership
        response = client.post(url, {"a1-selected": True, "a2-selected": True, 
                '0aaa6-selected': False, '0aaa0-selected': False, '0aaa1-selected': True})
        self.assertEqual(response.status_code, 302)
        # both still in for A1
        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0], activity__slug="a1")
        self.assertEqual(set(gm.student.person.userid for gm in gms), set([userid2,userid3]))
        # 0aaa1 added for A2
        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0], activity__slug="a2")
        self.assertEqual(set(gm.student.person.userid for gm in gms), set([userid3]))
        
        # remove member form
        url = reverse('offering:groups:remove_student', kwargs={'course_slug': c.slug, 'group_slug': "g-test-group"})
        response = basic_page_tests(self, client, url)
        
        # submit remove member
        response = client.post(url, {'0aaa6_a1-selected': True, '0aaa0_a1-selected': False, '0aaa1_a1-selected': True})
        self.assertEqual(response.status_code, 302)
        # 0aaa1 gone for A1
        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0], activity__slug="a1")
        self.assertEqual(set(gm.student.person.userid for gm in gms), set([userid2]))
        # 0aaa1 still there for A2
        gms = GroupMember.objects.filter(group__courseoffering=c, group=gs[0], activity__slug="a2")
        self.assertEqual(set(gm.student.person.userid for gm in gms), set([userid3]))

        # rename group form
        url = reverse('offering:groups:change_name', kwargs={'course_slug': c.slug, 'group_slug': "g-test-group"})
        response = basic_page_tests(self, client, url)
        
        # submit change name
        response = client.post(url, {'name': 'otherName'})
        self.assertEqual(response.status_code, 302)
        g = Group.objects.get(courseoffering=c)
        self.assertEqual(g.name, 'otherName')
        self.assertEqual(g.slug, 'g-test-group')

        # recheck basic view with more data        
        url = reverse('offering:groups:groupmanage', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)

        url = reverse('offering:groups:view_group', kwargs={'course_slug': c.slug, 'group_slug': "g-test-group"})
        response = basic_page_tests(self, client, url)

        
        
        
        
        

