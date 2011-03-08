from django.test import TestCase
from grades.formulas import *
from grades.models import *
from grades.utils import *
from coredata.models import *
from submission.models import StudentSubmission
from coredata.tests import create_offering
import pickle

from django.test.client import Client
from settings import CAS_SERVER_URL
from courselib.testing import *

# TODO: test activity modifiers ([A1.max], [A1.percent], [A1.final])

test_formulas = [ # expression, correct-result pairs
        ("-[A1] + +2", -8),
        ("9 + 2 - 3", 8),
        ("9 + 2 * 3", 15),
        ("(9 + 2) * 3", 33),
        ("[A1]/20+-3", -2.5),
        ("[Assignment #1]/20+-3", -2.5),
        ("SUM(1, 12.5, 3.4e2)", 353.5),
        ("SUM([A1]*2,[A2]/2)", 35),
        ("MAX([A1],[A2])", 30),
        ("max([A1],[A2])", 30),
        ("Min([A1],[A2], 12)", 10),
        ("AVG([A1],[A2], 12)", 17.3333333333333),
        (u"BEST(2, [A1], [A2])", 40),
        (u"BEST(2, [A1], [\u00b6],[A2], 12,-123)", 42),
        (u"BEST(3, [A1], [\u00b6],[A2], 12,123   )  ", 165),
        (u"[\u00b6] + 1", 5.5),
        ]

class GradesTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        pass

    def test_formulas(self):
        """
        Test the formula parsing & evaluation.
        """
        # set up course and related data
        s, c = create_offering()
        p = Person.objects.get(userid="0kvm")
        m = Member(person=p, offering=c, role="STUD", credits=3, added_reason="UNK")
        m.save()
       
        a = NumericActivity(name="Paragraph", short_name=u"\u00b6", status="RLS", offering=c, position=3, max_grade=40)
        a.save()
        g = NumericGrade(activity=a, member=m, value="4.5", flag="CALC")
        g.save()
        a = NumericActivity(name="Assignment #1", short_name="A1", status="RLS", offering=c, position=1, max_grade=15)
        a.save()
        g = NumericGrade(activity=a, member=m, value=10, flag="GRAD")
        g.save()
        a = NumericActivity(name="Assignment #2", short_name="A2", status="URLS", offering=c, position=2, max_grade=40)
        a.save()
        g = NumericGrade(activity=a, member=m, value=30, flag="GRAD")
        g.save()
        
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        
        # make sure a formula can be pickled and unpickled safely (i.e. can be cached)
        tree = parse("sum([Assignment #1], [A1], [A2])/20*-3")
        p = pickle.dumps(tree)
        tree2 = pickle.loads(p)
        self.assertEqual(tree, tree2)
        # check that it found the right list of columns used
        self.assertEqual(cols_used(tree), set(['A1', 'A2', 'Assignment #1']))
        
        # test parsing and evaluation to make sure we get the right values out
        for expr, correct in test_formulas:
            tree = parse(expr)
            res = eval_parse(tree, act_dict, m, False)
            self.assertAlmostEqual(correct, res, msg=u"Incorrect result for %s"%(expr,))

        # test some badly-formed stuff for appropriate exceptions
        tree = parse("1 + BEST(3, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, act_dict, m, True)
        tree = parse("1 + BEST(0, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, act_dict, m, True)
        tree = parse("[Foo] /2")
        self.assertRaises(KeyError, eval_parse, tree, act_dict, m, True)
        tree = parse("[a1] /2")
        self.assertRaises(KeyError, eval_parse, tree, act_dict, m, True)
        
        self.assertRaises(ParseException, parse, "AVG()")
        self.assertRaises(ParseException, parse, "(2+3*84")
        self.assertRaises(ParseException, parse, "2+3**84")
        self.assertRaises(ParseException, parse, "AVG(2,3,4")
        
        # test visible/invisible switching
        tree = parse("[Assignment #2]")
        res = eval_parse(tree, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        res = eval_parse(tree, act_dict, m, False)
        self.assertAlmostEqual(res, 30.0)

        # test unreleased/missing grade conditions
        expr = "[Assignment #2]"
        tree = parse(expr)
        
        # unrelased assignment (with grade)
        a.status='URLS'
        a.save()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        
        # explicit no grade (relased assignment)
        g.flag="NOGR"
        g.save()
        a.status='RLS'
        a.save()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)

        # no grade in database (relased assignment)
        g.delete()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        

    def test_activities(self):
        """
        Test activity classes: subclasses, selection, sorting.
        """
        s, c = create_offering()
       
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15)
        a.save()
        a = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=c, position=6, max_grade=15)
        a.save()
        a = LetterActivity(name="Project", short_name="Proj", status="URLS", offering=c, position=1)
        a.save()
        a = CalNumericActivity(name="Total", short_name="Total", status="URLS", offering=c, position=42, max_grade=30, formula="[A1]+[A2]")
        a.save()
       
        allact = all_activities_filter(offering=c)
        self.assertEqual(len(allact), 4)
        self.assertEqual(allact[0].slug, 'proj') # make sure position=1 is first
        self.assertEqual(type(allact[1]), NumericActivity)
        self.assertEqual(type(allact[3]), CalNumericActivity)
        
    def test_activity_pages(self):
        """
        Test pages around activities
        """
        s, c = create_offering()

        # add some assignments and members
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, percent=10)
        a.save()
        a1=a
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        p = Person.objects.get(userid="ggbaker")
        m = Member(person=p, offering=c, role="INST", added_reason="UNK")
        m.save()
        p = Person.objects.get(userid="0kvm")
        m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
        m.save()
        
        # test instructor pages
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)

        response = basic_page_tests(self, client, '/' + c.slug + '/')
        self.assertContains(response, 'href="' + reverse('groups.views.groupmanage', kwargs={'course_slug':c.slug}) +'"')

        basic_page_tests(self, client, c.get_absolute_url())
        basic_page_tests(self, client, c.get_absolute_url() + '_students/0kvm')
        basic_page_tests(self, client, reverse('grades.views.add_numeric_activity', kwargs={'course_slug':c.slug}))
        basic_page_tests(self, client, reverse('grades.views.add_letter_activity', kwargs={'course_slug':c.slug}))

        # test student pages
        client = Client()
        client.login(ticket="0kvm", service=CAS_SERVER_URL)
        response = basic_page_tests(self, client, '/' + c.slug + '/')
        self.assertContains(response, "Gregory Baker")
        self.assertContains(response, 'href="' + reverse('groups.views.groupmanage', kwargs={'course_slug':c.slug}) +'"')

        response = basic_page_tests(self, client, a.get_absolute_url())
        # small class (one student) shouldn't contain summary stats
        self.assertNotContains(response, "Histogram")
        self.assertNotContains(response, "Standard Deviation")

    def test_instructor_workflow(self):
        """
        Work through the site as an instructor
        """
        s, c = create_offering()
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
        
        # course main screen
        url = reverse('grades.views.course_info', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        url = reverse('grades.views.add_numeric_activity', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="' + url +'"')
        
        # add activity
        import datetime
        now = datetime.datetime.now()
        due = now + datetime.timedelta(days=7)
        response = client.post(url, {'name':'Assignment 1', 'short_name':'A1', 'status':'URLS', 'due_date_0':due.strftime('%Y-%m-%d'), 'due_date_1':due.strftime('%H:%M:%S'), 'percent': '10', 'group': '1', 'max_grade': 25, 'extend_group': 'None'})
        self.assertEquals(response.status_code, 302)
        
        acts = NumericActivity.objects.filter(offering=c)
        self.assertEquals(len(acts), 1)
        a = acts[0]
        self.assertEquals(a.name, "Assignment 1")
        self.assertEquals(a.slug, "a1")
        self.assertEquals(a.max_grade, 25)
        self.assertEquals(a.group, False)
        self.assertEquals(a.deleted, False)
        
        # add calculated numeric activity
        url = reverse('grades.views.add_cal_numeric_activity', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'name':'Total', 'short_name':'Total', 'status':'URLS', 'group': '1', 'max_grade': 30, 'formula': '[A1]+5'})
        self.assertEquals(response.status_code, 302)

        acts = CalNumericActivity.objects.filter(offering=c)
        self.assertEquals(len(acts), 1)
        a = acts[0]
        self.assertEquals(a.slug, "total")
        self.assertEquals(a.max_grade, 30)
        self.assertEquals(a.group, False)
        self.assertEquals(a.deleted, False)
        self.assertEquals(a.formula, '[A1]+5')
        
        # formula tester
        url = reverse('grades.views.formula_tester', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'formula': '[A1]+5', 'a1-status': 'RLS', 'a1-value': '6', 'total-status': 'URLS'})
        self.assertContains(response, '<div id="formula_result">11.0</div>')
        validate_content(self, response.content, url)
        
    def test_activity_status(self):
        """
        Test operations on activity's status
        """
        # check the get_status_display override
        now = datetime.datetime.now()
        a = NumericActivity(name="Assign 1", short_name="A1", status="INVI", max_grade=10)
        self.assertEquals(a.get_status_display(), ACTIVITY_STATUS["INVI"])
        a.status="RLS"
        self.assertEquals(a.get_status_display(), ACTIVITY_STATUS["RLS"])
        a.status="URLS"
        self.assertEquals(a.get_status_display(), ACTIVITY_STATUS["URLS"])
        a.due_date = now - datetime.timedelta(hours=1)
        self.assertEquals(a.get_status_display(), ACTIVITY_STATUS["URLS"])
        # the special case: unreleased, before the due date
        a.due_date = now + datetime.timedelta(hours=1)
        self.assertEquals(a.get_status_display(), "no grades: due date not passed")
        
    def test_group_change(self):
        """
        Test changing group <-> individual on an activity.  Should only be possible in some conditions.
        """
        s, c = create_offering()

        # add some assignments and members
        due = datetime.datetime.now() + datetime.timedelta(days=1)
        due_date = str(due.date())
        due_time = due.time().strftime("%H:%M:%S")
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, percent=10, due_date=due, group=False)
        a.save()
        p = Person.objects.get(userid="ggbaker")
        m = Member(person=p, offering=c, role="INST", added_reason="UNK")
        m.save()
        p = Person.objects.get(userid="0kvm")
        m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
        m.save()
        
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        url = reverse('grades.views.edit_activity', kwargs={'course_slug': c.slug, 'activity_slug': a.slug})

        # for whatever reason, '0' is group and '1' is individual for the group value
        submit_dict = {'name': a.name, 'short_name': a.short_name, 'status': a.status, 'due_date_0': due_date, 'due_date_1': due_time, 'percent': a.percent, 'max_grade': a.max_grade, 'group': '1', 'extend_group': 'None'}
        # no change
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 302) # successful submit -> redirect
        self.assertEquals(NumericActivity.objects.get(id=a.id).group, False)

        # change indiv -> group
        submit_dict['group'] = '0'
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(NumericActivity.objects.get(id=a.id).group, True)
        
        # try with activity past due
        a.due_date = datetime.datetime.now() - datetime.timedelta(days=1)
        a.save()
        submit_dict['due_date_0'] = str(a.due_date.date())
        submit_dict['group'] = '0'
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 200) # error on form -> 200 and back to form with error
        self.assertContains(response, "due date has passed")
        
        # try with a mark in the system
        a.due_date = datetime.datetime.now() + datetime.timedelta(days=1)
        a.save()
        submit_dict['due_date_0'] = str(a.due_date.date())
        submit_dict['group'] = '0'
        g = NumericGrade(activity=a, member=m, value=2, flag="GRAD")
        g.save()
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "grades have already been given")
        
        # try with a submission in the system
        g.flag = "NOGR"
        g.save()
        s = StudentSubmission(activity=a, member=m)
        s.save()
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "submissions have already been made")
        
    def test_grade_range_stat(self):
        student_grade_list = [10, 10, 10, 100, 100, 0, 0, 5, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('0-10',3), ('10-20',3), ('20-30',1), ('30-40',0), ('40-50',0), ('50-60',0), ('60-70',0),('70-80',0),('80-90',0),('90-100',2)]
        self.assertEquals(res, expect)

        student_grade_list = [10, 10, 10, 100.01, 100, 0, 0, 5, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('0-10',3), ('10-20',3), ('20-30',1), ('30-40',0), ('40-50',0), ('50-60',0), ('60-70',0),('70-80',0),('80-90',0),('90-100',0),('100-110',2)]
        self.assertEquals(res, expect)

        student_grade_list = [20, 20, 20, 20, 20, 20, 20, 20, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('0-10',0), ('10-20',0), ('20-30',9), ('30-40',0), ('40-50',0), ('50-60',0), ('60-70',0),('70-80',0),('80-90',0),('90-100',0)]
        self.assertEquals(res, expect)

        student_grade_list = [-20, -20, -20, -20, -10, -10, -10, -10]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('-20--10',4),('-10-0',4), ('0-10',0), ('10-20',0), ('20-30',0), ('30-40',0), ('40-50',0), ('50-60',0), ('60-70',0),('70-80',0),('80-90',0),('90-100',0)]
        self.assertEquals(res, expect)

        student_grade_list = [-20.1, -20, -20, -20, -10, -10, -10, -10]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('-30--20',1), ('-20--10',3), ('-10-0',4), ('0-10',0), ('10-20',0), ('20-30',0), ('30-40',0), ('40-50',0), ('50-60',0), ('60-70',0),('70-80',0),('80-90',0),('90-100',0)]
        self.assertEquals(res, expect)
