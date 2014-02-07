from django.test import TestCase
from grades.formulas import parse, cols_used, eval_parse, EvalException, ParseException
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity, \
    NumericGrade, LetterGrade, GradeHistory, all_activities_filter, ACTIVITY_STATUS, sorted_letters, \
    median_letters
from grades.utils import activities_dictionary, generate_grade_range_stat
from coredata.models import Person, Member, CourseOffering
from dashboard.models import UserConfig
from submission.models import StudentSubmission
from coredata.tests import create_offering
import pickle, datetime, decimal

from django.conf import settings
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
        (u"BEST(4, 1.0, 0.8, 0.0, 1.0, 0.5)", 3.3),
        (u"BEST(4, 1.0, 0.2, 0.5, 0.0,	0.0)", 1.7)
        ]

class GradesTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        self.course_slug=TEST_COURSE_SLUG

    def test_formulas(self):
        """
        Test the formula parsing & evaluation.
        """
        # set up course and related data
        s, c = create_offering()
        p = Person.objects.get(userid="0aaa0")
        m = Member(person=p, offering=c, role="STUD", credits=3, added_reason="UNK")
        m.save()
       
        a = NumericActivity(name="Paragraph", short_name=u"\u00b6", status="RLS", offering=c, position=3, max_grade=40, percent=5)
        a.save()
        g = NumericGrade(activity=a, member=m, value="4.5", flag="CALC")
        g.save(entered_by='ggbaker')
        a1 = NumericActivity(name="Assignment #1", short_name="A1", status="RLS", offering=c, position=1, max_grade=15, percent=10)
        a1.save()
        g = NumericGrade(activity=a1, member=m, value=10, flag="GRAD")
        g.save(entered_by='ggbaker')
        a2 = NumericActivity(name="Assignment #2", short_name="A2", status="URLS", offering=c, position=2, max_grade=40, percent=20)
        a2.save(entered_by='ggbaker')
        g = NumericGrade(activity=a2, member=m, value=30, flag="GRAD")
        g.save(entered_by='ggbaker')
        
        ca = CalNumericActivity(name="Final Grade", short_name=u"FG", status="RLS", offering=c, position=4, max_grade=1)
        ca.save()
        
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        
        # make sure a formula can be pickled and unpickled safely (i.e. can be cached)
        tree = parse("sum([Assignment #1], [A1], [A2])/20*-3", c, ca)
        p = pickle.dumps(tree)
        tree2 = pickle.loads(p)
        self.assertEqual(tree, tree2)
        # check that it found the right list of columns used
        self.assertEqual(cols_used(tree), set(['A1', 'A2', 'Assignment #1']))
        
        # test parsing and evaluation to make sure we get the right values out
        for expr, correct in test_formulas:
            tree = parse(expr, c, ca)
            res = eval_parse(tree, ca, act_dict, m, False)
            self.assertAlmostEqual(correct, res, msg=u"Incorrect result for %s"%(expr,))

        # test some badly-formed stuff for appropriate exceptions
        tree = parse("1 + BEST(3, [A1], [A2])", c, ca)
        self.assertRaises(EvalException, eval_parse, tree, ca, act_dict, m, True)
        tree = parse("1 + BEST(0, [A1], [A2])", c, ca)
        self.assertRaises(EvalException, eval_parse, tree, ca, act_dict, m, True)
        tree = parse("[Foo] /2", c, ca)
        self.assertRaises(KeyError, eval_parse, tree, ca, act_dict, m, True)
        tree = parse("[a1] /2", c, ca)
        self.assertRaises(KeyError, eval_parse, tree, ca, act_dict, m, True)
        
        self.assertRaises(ParseException, parse, "AVG()", c, ca)
        self.assertRaises(ParseException, parse, "(2+3*84", c, ca)
        self.assertRaises(ParseException, parse, "2+3**84", c, ca)
        self.assertRaises(ParseException, parse, "AVG(2,3,4", c, ca)
        self.assertRaises(ParseException, parse, "{something}", c, ca)
        
        # test visible/invisible switching
        tree = parse("[Assignment #2]", c, ca)
        res = eval_parse(tree, ca, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        res = eval_parse(tree, ca, act_dict, m, False)
        self.assertAlmostEqual(res, 30.0)

        # test unreleased/missing grade conditions
        expr = "[Assignment #2]"
        tree = parse(expr, c, ca)
        
        # unrelased assignment (with grade)
        a2.status='URLS'
        a2.save()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, ca, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        
        # explicit no grade (relased assignment)
        g.flag="NOGR"
        g.save(entered_by='ggbaker')
        a2.status='RLS'
        a2.save(entered_by='ggbaker')
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, ca, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)

        # no grade in database (relased assignment)
        g.delete()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, ca, act_dict, m, True)
        self.assertAlmostEqual(res, 0.0)
        
        # test [[activitytotal]]
        expr = "[[activitytotal]]"
        tree = parse(expr, c, ca)
        res = eval_parse(tree, ca, act_dict, m, True)
        self.assertAlmostEqual(res, 7.229166666)
        

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
        p = Person.objects.get(userid="0aaa0")
        m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
        m.save()
        
        # test instructor pages
        client = Client()
        client.login_user("ggbaker")

        response = basic_page_tests(self, client, '/' + c.slug + '/')
        self.assertContains(response, 'href="' + reverse('groups.views.groupmanage', kwargs={'course_slug':c.slug}) +'"')

        basic_page_tests(self, client, c.get_absolute_url())
        basic_page_tests(self, client, reverse('grades.views.student_info', kwargs={'course_slug': c.slug, 'userid': '0aaa0'}))
        basic_page_tests(self, client, reverse('grades.views.add_numeric_activity', kwargs={'course_slug':c.slug}))
        basic_page_tests(self, client, reverse('grades.views.add_letter_activity', kwargs={'course_slug':c.slug}))

        # test student pages
        client = Client()
        client.login_user("0aaa0")
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
        userid1 = "0bbb0"
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
        
        # course main screen
        url = reverse('grades.views.course_info', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        url = reverse('grades.views.activity_choice', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="' + url +'"')
        url = reverse('grades.views.add_numeric_activity', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        
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
        response = client.get(url, {'formula': '[A1]+5', 'a1-status': 'RLS', 'a1-value': '6', 'total-status': 'URLS'})
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
        p = Person.objects.get(userid="0aaa0")
        m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
        m.save()
        
        client = Client()
        client.login_user("ggbaker")
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
        g.save(entered_by='ggbaker')
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "grades have already been given")
        
        # try with a submission in the system
        g.flag = "NOGR"
        g.save(entered_by='ggbaker')
        s = StudentSubmission(activity=a, member=m)
        s.save()
        response = client.post(url, submit_dict)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "submissions have already been made")
        
    def test_grade_range_stat(self):
        student_grade_list = [10, 10, 10, 100, 100, 0, 0, 5, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [(u'0\u201310%',3), (u'10\u201320%',3), (u'20\u201330%',1), (u'30\u201340%',0), (u'40\u201350%',0), (u'50\u201360%',0), (u'60\u201370%',0),(u'70\u201380%',0),(u'80\u201390%',0),(u'90\u2013100%',2)]
        self.assertEquals(res, expect)

        student_grade_list = [10, 10, 10, 100.01, 100, 0, 0, 5, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [(u'0\u201310%',3), (u'10\u201320%',3), (u'20\u201330%',1), (u'30\u201340%',0), (u'40\u201350%',0), (u'50\u201360%',0), (u'60\u201370%',0),(u'70\u201380%',0),(u'80\u201390%',0),(u'90\u2013100%',1),('>100%',1)]
        self.assertEquals(res, expect)

        student_grade_list = [20, 20, 20, 20, 20, 20, 20, 20, 20]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [(u'0\u201310%',0), (u'10\u201320%',0), (u'20\u201330%',9), (u'30\u201340%',0), (u'40\u201350%',0), (u'50\u201360%',0), (u'60\u201370%',0),(u'70\u201380%',0),(u'80\u201390%',0),(u'90\u2013100%',0)]
        self.assertEquals(res, expect)

        student_grade_list = [-20, -20, -20, -20, -10, -10, -10, -10]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('<0%',8), (u'0\u201310%',0), (u'10\u201320%',0), (u'20\u201330%',0), (u'30\u201340%',0), (u'40\u201350%',0), (u'50\u201360%',0), (u'60\u201370%',0),(u'70\u201380%',0),(u'80\u201390%',0),(u'90\u2013100%',0)]
        self.assertEquals(res, expect)

        student_grade_list = [-20.1, -20, -20, -20, -10, -10, -10, -10]
        grade_range_list = generate_grade_range_stat(student_grade_list, 10)
        res = [(i.grade_range, i.stud_count) for i in grade_range_list]
        expect = [('<0%',8), (u'0\u201310%',0), (u'10\u201320%',0), (u'20\u201330%',0), (u'30\u201340%',0), (u'40\u201350%',0), (u'50\u201360%',0), (u'60\u201370%',0),(u'70\u201380%',0),(u'80\u201390%',0),(u'90\u2013100%',0)]
        self.assertEquals(res, expect)

    def test_calc_letter(self):
        """
        Test calculated letter functionality
        """
        s, c = create_offering()
        na = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, percent=10, group=False)
        na.save()
        
        a = CalLetterActivity(offering=c, name="A1 Letter", short_name="A1L", status="RLS", numeric_activity=na, exam_activity=None, position=3)
        a.save()
        
        # test cutoff getter/setter
        cs = a.get_cutoffs()
        cs[1] = decimal.Decimal('271') / decimal.Decimal('3')
        a.set_cutoffs(cs)
        s.save()
        cs = a.get_cutoffs()
        self.assertAlmostEquals(float(cs[1]), 90.333333333333)

    def test_sort_letter(self):
        """
        Test sorting letter grades
        """
        s, c = create_offering()
        
        a = LetterActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, due_date=None, group=False)
        a.save()

        ms = []
        for i in range(20):
            p = Person.objects.get(userid="0aaa%i"%i)
            m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
            m.save()
            ms.append(m)
        
        g = LetterGrade(activity=a, member=ms[0], letter_grade="B+", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[1], letter_grade="A", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[2], letter_grade="D", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[3], letter_grade="B-", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[4], letter_grade="B", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[5], letter_grade="A+", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[6], letter_grade="F", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[7], letter_grade="DE", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[8], letter_grade="C-", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[9], letter_grade="N", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[10], letter_grade="N", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[11], letter_grade="P", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[12], letter_grade="GN", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[13], letter_grade="N", flag="GRAD")
        g.save(entered_by='ggbaker')
        g = LetterGrade(activity=a, member=ms[14], letter_grade="A", flag="GRAD")
        g.save(entered_by='ggbaker')
        
        g_objs = LetterGrade.objects.filter(activity=a)
        gs = [g.letter_grade for g in g_objs]
        gs_sort = sorted_letters(gs)
        self.assertEquals(gs_sort, ['A+', 'A', 'A', 'B+', 'B', 'B-', 'C-', 'D', 'P', 'F', 'DE', 'N', 'N', 'N', 'GN'])
        
        # pre-sort by userid for median testing (so we know which subsets we're grabbing)
        gs = [(int(g.member.person.userid[4:]), g.letter_grade) for g in g_objs]
        gs.sort()
        gs = [g for u,g in gs]

        # odd-length case
        self.assertEquals(median_letters(sorted_letters(gs[0:5])), "B")
        # even length with median at boundary
        self.assertEquals(median_letters(sorted_letters(gs[0:6])), "B+/B")
        # even length with median not at boundary
        grades = [gs[1], gs[2], gs[5], gs[14]] # [A, C-, A+, A]
        self.assertEquals(median_letters(sorted_letters(grades)), "A")
        # empty list
        self.assertEquals(median_letters([]), u"\u2014")


        
    def test_out_of_zero(self):
        """
        Test activities out of zero
        """
        c = CourseOffering.objects.get(slug=self.course_slug)
        a = NumericActivity(offering=c, name="AZero", short_name="AZ", status="RLS", group=False, deleted=False, max_grade=0, position=1)
        a.save()
        stud = c.member_set.filter(role="STUD")[0]
        
        # test as instructor
        client = Client()
        client.login_user("ggbaker")
        
        url = reverse('marking.views.change_grade_status', kwargs={'course_slug': c.slug, 'activity_slug': a.slug, 'userid': stud.person.userid})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "out of 0")

        response = client.post(url, {'grade-status-value': 3, 'grade-status-flag': 'GRAD', 'grade-status-comment': ''})
        self.assertEquals(response.status_code, 302)
        g = NumericGrade.objects.get(activity=a, member=stud)
        self.assertEquals(g.value, 3)
        
        url = reverse('grades.views.activity_info', kwargs={'course_slug': c.slug, 'activity_slug': a.slug})
        response = basic_page_tests(self, client, url)
        url = reverse('grades.views.student_info', kwargs={'course_slug': c.slug, 'userid': stud.person.userid})
        response = basic_page_tests(self, client, url)

        # test as student
        client.login_user(stud.person.userid)

        url = reverse('grades.views.course_info', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        url = reverse('grades.views.activity_info', kwargs={'course_slug': c.slug, 'activity_slug': a.slug})
        response = basic_page_tests(self, client, url)


    def test_replace_activity(self):
        """
        Can we safely replace an activity with one of the same name/shortname?
        """
        c = CourseOffering.objects.get(slug=self.course_slug)
        a = NumericActivity(offering=c, name="Assign1", short_name="A1", status="RLS", group=False, deleted=False, max_grade=10, position=1)
        a.save()
        
        a.safely_delete()
        self.assertEqual(a.deleted, True)
        self.assertNotEqual(a.name, 'Assign1')
        self.assertNotEqual(a.short_name, 'A1')
        
        # replace with same type
        a = CalNumericActivity(offering=c, name="Assign1", short_name="A1", status="URLS", group=True, deleted=False, max_grade=15, position=2)
        a.save()
        a.safely_delete()
        
        # replace with a different type
        a = LetterActivity(offering=c, name="Assign1", short_name="A1", status="RLS", group=False, deleted=False, position=3)
        a.save()


    def test_grade_assign(self):
        """
        Test various grade-assigning frontend interactions.
        """
        client = Client()
        client.login_user("ggbaker")

        o = CourseOffering.objects.get(slug=self.course_slug)
        a = Activity.objects.get(offering=o, slug='a1')
        m = Member.objects.get(offering=o, person__userid='0aaa0')

        # grade status form
        url = reverse('marking.views.change_grade_status', kwargs={'course_slug': o.slug, 'activity_slug': a.slug, 'userid': m.person.userid})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'grade-status-value': '6', 'grade-status-flag': 'DISH', 'grade-status-comment': 'the comment'})
        self.assertEquals(response.status_code, 302)

        ng = NumericGrade.objects.get(member=m, activity=a)
        self.assertEquals(ng.value, 6)
        self.assertEquals(ng.flag, 'DISH')
        self.assertEquals(ng.comment, 'the comment')

        # grade all students
        url = reverse('marking.views.mark_all_students', kwargs={'course_slug': o.slug, 'activity_slug': a.slug})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'0aaa0-value': '7', '0aaa1-value': '8'})
        self.assertEquals(response.status_code, 302)

        ng = NumericGrade.objects.get(member=m, activity=a)
        self.assertEquals(ng.value, 7)
        self.assertEquals(ng.flag, 'GRAD')
        ng = NumericGrade.objects.get(member__person__userid='0aaa1', activity=a)
        self.assertEquals(ng.value, 8)
        self.assertEquals(ng.flag, 'GRAD')

        # detailed marking
        url = reverse('marking.views.marking_student', kwargs={'course_slug': o.slug, 'activity_slug': a.slug, 'userid': m.person.userid})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'cmp-1-value': '2', 'cmp-1-comment': 'comment1', 'cmp-2-value': '3', 'cmp-2-comment': 'comment2',
                                     'late_penalty': '0', 'mark_adjustment': '0'})
        self.assertEquals(response.status_code, 302)
        ng = NumericGrade.objects.get(member=m, activity=a)
        self.assertEquals(ng.value, 5)
        self.assertEquals(ng.flag, 'GRAD')

        # student summary page
        url = reverse('grades.views.student_info', kwargs={'course_slug': o.slug, 'userid': m.person.userid})
        response = basic_page_tests(self, client, url)

        # check GradeHistory objects
        ghs = GradeHistory.objects.filter(activity=a, member=m)
        self.assertEquals(ghs.count(), 3)




class PagesTests(TestCase):
    fixtures = ['test_data']

    def test_course_level(self):
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        na = NumericActivity.objects.filter(offering=crs, group=True)[0]
        la = LetterActivity.objects.filter(offering=crs, group=True)[0]
        cna = CalNumericActivity.objects.filter(offering=crs)[0]
        cla = CalLetterActivity.objects.filter(offering=crs)[0]

        instr = Member.objects.filter(offering=crs, role='INST')[0]
        student = Member.objects.filter(offering=crs, role='STUD')[0]
        c = Client()
        
        # as instructor
        c.login_user(instr.person.userid)
        UserConfig(user=instr.person, key='photo-agreement', value={'agree':True}).save()
        test_views(self, c, 'grades.views.', ['course_config', 'course_info', 'add_numeric_activity',
                'add_cal_numeric_activity', 'add_letter_activity', 'add_cal_letter_activity', 'formula_tester',
                'all_grades', 'class_list', 'photo_list', 'student_search', 'new_message'],
                {'course_slug': crs.slug})
        test_views(self, c, 'grades.views.', ['student_info'],
                {'course_slug': crs.slug, 'userid': student.person.userid})
        
        # various combinations of activity type and view
        test_views(self, c, 'grades.views.', ['activity_info', 'activity_info_with_groups', 'activity_stat',
                'edit_activity'],
                {'course_slug': crs.slug, 'activity_slug': na.slug})
        test_views(self, c, 'grades.views.', ['compare_official', 'activity_info',
                'activity_info_with_groups', 'activity_stat', 'edit_activity'],
                {'course_slug': crs.slug, 'activity_slug': la.slug})
        test_views(self, c, 'grades.views.', ['activity_info', 'activity_stat', 'edit_activity'],
                {'course_slug': crs.slug, 'activity_slug': cna.slug})
        test_views(self, c, 'grades.views.', ['edit_cutoffs', 'compare_official', 'activity_info',
                'activity_stat', 'edit_activity'],
                {'course_slug': crs.slug, 'activity_slug': cla.slug})

        # as student
        c.login_user(student.person.userid)
        test_views(self, c, 'grades.views.', ['course_info'],
                {'course_slug': crs.slug})
        test_views(self, c, 'grades.views.', ['activity_info'],
                {'course_slug': crs.slug, 'activity_slug': na.slug})



