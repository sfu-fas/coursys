from django.test import TestCase
from django.core.urlresolvers import reverse
import json, datetime
from coredata.models import Person, Semester, Role
from grad.models import GradStudent, GradRequirement, GradProgram, Letter, LetterTemplate, \
        Supervisor, GradStatus, CompletedRequirement, ScholarshipType, Scholarship, OtherFunding, \
        Promise, GradProgramHistory, FinancialComment
from courselib.testing import basic_page_tests, test_auth, Client, test_views
from grad.views.view import all_sections
from django.http import QueryDict
from grad.forms import SearchForm

class GradTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        # find a grad student who is owned by CS for testing
        gs = GradStudent.objects.filter(program__unit__slug='cmpt')[0]
        self.gs_userid = gs.person.userid

    def test_grad_quicksearch(self):
        """
        Tests grad quicksearch (index page) functionality
        """
        client = Client()
        test_auth(client, 'ggbaker')
        response = client.get(reverse('grad.views.index'))
        self.assertEqual(response.status_code, 200)
        
        # AJAX calls for autocomplete return JSON
        response = client.get(reverse('grad.views.quick_search')+'?term=grad')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        # get this grad's slug from the search
        autocomplete = json.loads(response.content)
        grad_slug = [d['value'] for d in autocomplete if d['value'].startswith(self.gs_userid)][0]
        
        # search submit with gradstudent slug redirects to page
        response = client.get(reverse('grad.views.quick_search')+'?search='+grad_slug)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].endswith( reverse('grad.views.view', kwargs={'grad_slug': grad_slug}) ))

        # search submit with non-slug redirects to "did you mean" page
        response = client.get(reverse('grad.views.quick_search')+'?search=' + self.gs_userid[0:4])
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].endswith( reverse('grad.views.not_found')+"?search=" + self.gs_userid[0:4] ))
        
        response = client.get(response['location'])
        gradlist = response.context['grads']
        self.assertEqual(len(gradlist), 1)
        self.assertEqual(gradlist[0], GradStudent.objects.get(person__userid=self.gs_userid))

    def test_that_grad_search_returns_200_ok(self):
        """
        Tests that /grad/search is available.
        """
        client = Client()
        test_auth(client, 'ggbaker')
        response = client.get(reverse('grad.views.search'))
        self.assertEqual(response.status_code, 200)
    
    def test_that_grad_search_with_csv_option_returns_csv(self):
        client = Client()
        test_auth(client, 'ggbaker')
        response = client.get(reverse('grad.views.search'), {'columns':'person.first_name', 'csv':'sure'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_grad_pages(self):
        """
        Check overall pages for the grad module and make sure they all load
        """
        client = Client()
        test_auth(client, 'ggbaker')

        gs = self.__make_test_grad()
        prog = gs.program
        GradRequirement(program=prog, description="Some New Requirement").save()
        Supervisor(student=GradStudent.objects.all()[0], supervisor=Person.objects.get(userid='ggbaker'), supervisor_type='SEN').save()
        lt = LetterTemplate(unit=gs.program.unit, label='Template', content="This is the\n\nletter for {{first_name}}.")
        lt.save()

        test_views(self, client, 'grad.views.',
                ['programs', 'new_program', 'requirements', 'new_requirement', 'letter_templates',
                 'new_letter_template', 'manage_scholarshipType', 'search', 'funding_report', 'all_promises'],
                {})
        test_views(self, client, 'grad.views.', ['manage_letter_template'], {'letter_template_slug': lt.slug})
        test_views(self, client, 'grad.views.', ['not_found'], {}, qs='search=grad')


    def __make_test_grad(self):
        gs = GradStudent.objects.get(person__userid=self.gs_userid)
        sem = Semester.current()
        
        # put some data there so there's something to see in the tests (also, the empty <tbody>s don't validate)
        req = GradRequirement(program=gs.program, description="Some Requirement")
        req.save()
        st = ScholarshipType(unit=gs.program.unit, name="Some Scholarship")
        st.save()
        Supervisor(student=gs, supervisor=Person.objects.get(userid='ggbaker'), supervisor_type='SEN').save()
        GradProgramHistory(student=gs, program=gs.program).save()
        GradStatus(student=gs, status='ACTI', start=sem).save()
        CompletedRequirement(student=gs, requirement=req, semester=sem).save()
        Scholarship(student=gs, scholarship_type=st, amount=1000, start_semester=sem, end_semester=sem).save()
        OtherFunding(student=gs, amount=100, semester=sem, description="Some Other Funding", comments="Other Funding\n\nComment").save()
        Promise(student=gs, amount=10000, start_semester=sem, end_semester=sem.next_semester()).save()
        FinancialComment(student=gs, semester=sem, comment_type='SCO', comment='Some comment.\nMore.', created_by='ggbaker').save()
        Supervisor(student=gs, supervisor=Person.objects.get(userid='ggbaker'), supervisor_type='SEN').save()
        
        return gs




    def test_grad_student_pages(self):
        """
        Check the pages for a grad student and make sure they all load
        """
        client = Client()
        test_auth(client, 'ggbaker')
        gs = self.__make_test_grad()
        lt = LetterTemplate(unit=gs.program.unit, label='Template', content="This is the\n\nletter for {{first_name}}.")
        lt.save()

        url = reverse('grad.views.get_letter_text', kwargs={'grad_slug': gs.slug, 'letter_template_id': lt.id})
        content = client.get(url).content
        Letter(student=gs, template=lt, date=datetime.date.today(), content=content).save()
        
        url = reverse('grad.views.view', kwargs={'grad_slug': gs.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        # sections of the main gradstudent view that can be loaded
        for section in all_sections:
            url = reverse('grad.views.view', kwargs={'grad_slug': gs.slug})
            # check fragment fetch for AJAX
            try:
                response = client.get(url, {'section': section})
                self.assertEqual(response.status_code, 200)
            except:
                print "with section==" + repr(section)
                raise

            # check section in page
            try:
                response = basic_page_tests(self, client, url + '?_escaped_fragment_=' + section)
                self.assertEqual(response.status_code, 200)
            except:
                print "with section==" + repr(section)
                raise
        
        # check all sections together
        url = url + '?_escaped_fragment_=' + ','.join(all_sections)
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
            
        # check management pages
        for view in ['financials', 'manage_general', 'manage_requirements', 'manage_scholarships',
                      'manage_otherfunding', 'manage_promises', 'manage_letters', 'manage_status', 'manage_supervisors',
                      'manage_program', 'manage_start_end_semesters', 'manage_financialcomments', 'manage_defence']:
            try:
                url = reverse('grad.views.'+view, kwargs={'grad_slug': gs.slug})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise

        url = reverse('grad.views.new_letter', kwargs={'grad_slug': gs.slug, 'letter_template_slug': lt.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        
    def test_grad_letters(self):
        """
        Check handling of letters for grad students
        """
        client = Client()
        test_auth(client, 'ggbaker')
        gs = GradStudent.objects.get(person__userid=self.gs_userid)

        # get template text and make sure substitutions are made
        lt = LetterTemplate.objects.get(label="Funding")
        url = reverse('grad.views.get_letter_text', kwargs={'grad_slug': gs.slug, 'letter_template_id': lt.id})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'M Grad is making satisfactory progress')
        content = unicode(response.content)
        
        # create a letter with that content
        l = Letter(student=gs, date=datetime.date.today(), to_lines="The Student\nSFU", template=lt, created_by='ggbaker', content=content)
        l.save()
        url = reverse('grad.views.view_letter', kwargs={'grad_slug': gs.slug, 'letter_slug': l.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        url = reverse('grad.views.copy_letter', kwargs={'grad_slug': gs.slug, 'letter_slug': l.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        
    def test_advanced_search_1(self):
        """
        Basics of the advanced search toolkit
        """
        from grad.forms import COLUMN_CHOICES, COLUMN_WIDTHS_DATA
        from grad.templatetags.getattribute import getattribute
        
        cols = set(k for k,v in COLUMN_CHOICES)
        widths = set(k for k,v in COLUMN_WIDTHS_DATA)
        self.assertEquals(cols, widths)
        
        gs = self.__make_test_grad()
        for key in cols:
            # make sure each column returns *something* without error
            getattribute(gs, key)

    def test_advanced_search_2(self):
        client = Client()
        test_auth(client, 'ggbaker')
        units = [r.unit for r in Role.objects.filter(person__userid='ggbaker', role='GRAD')]

        # basic search with the frontend
        url = reverse('grad.views.search', kwargs={})
        qs = 'student_status=PART&student_status=ACTI&columns=person.emplid&columns=person.userid&columns=program'
        response = basic_page_tests(self, client, url + '?' + qs)
        self.assertIn('grad/search_results.html', [t.name for t in response.templates])
        search_res_1 = response.context['grads']

        # test the searching API
        form = SearchForm(QueryDict(qs))
        search_res_2 = form.search_results(units)
        self.assertEqual(set(search_res_1), set(search_res_2))

        form = SearchForm(QueryDict('columns=person.emplid'))
        all_grads = form.search_results(units)
        gs = all_grads[0]

        # test student status search (which is a simple in-database query)
        gs.status = 'ACTI'
        gs.save()
        form = SearchForm(QueryDict('student_status=ACTI&columns=person.emplid'))
        status_search = form.search_results(units)
        self.assertIn(gs, status_search)
        form = SearchForm(QueryDict('student_status=LEAV&columns=person.emplid'))
        status_search = form.search_results(units)
        self.assertNotIn(gs, status_search)

        # test semester search (which a more difficult in-database query)
        sem = gs.start_semester
        form = SearchForm(QueryDict('start_semester_start=%s&columns=person.emplid' % (sem.name)))
        semester_search = form.search_results(units)
        self.assertIn(gs, semester_search)
        form = SearchForm(QueryDict('start_semester_start=%s&columns=person.emplid' % (sem.next_semester().name)))
        semester_search = form.search_results(units)
        self.assertNotIn(gs, semester_search)

        # test GPA searching (which is a secondary filter)
        gs.person.config['gpa'] = 4.2
        gs.person.save()
        form = SearchForm(QueryDict('gpa_min=4.1&columns=person.emplid'))
        high_gpa = form.search_results(units)
        self.assertIn(gs, high_gpa)

        gs.person.config['gpa'] = 2.2
        gs.person.save()
        form = SearchForm(QueryDict('gpa_min=4.1&columns=person.emplid'))
        high_gpa = form.search_results(units)
        self.assertNotIn(gs, high_gpa)







