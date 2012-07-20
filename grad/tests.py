from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
import json, datetime
from coredata.models import Person, Semester
from grad.models import GradStudent, GradRequirement, GradProgram, Letter, LetterTemplate, \
        Supervisor, GradStatus, CompletedRequirement, ScholarshipType, Scholarship, OtherFunding, \
        Promise
from courselib.testing import basic_page_tests
from grad.views.view import all_sections


class GradTest(TestCase):
    fixtures = ['test_data']

    def test_grad_quicksearch(self):
        """
        Tests grad quicksearch (index page) functionality
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('grad.views.index'))
        self.assertEqual(response.status_code, 200)
        
        # AJAX calls for autocomplete return JSON
        response = client.get(reverse('grad.views.quick_search')+'?term=grad')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        json.loads(response.content)
        
        # search submit with gradstudent slug redirects to page
        grad_slug = '0nnngrad-mscthesis'
        response = client.get(reverse('grad.views.quick_search')+'?search='+grad_slug)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].endswith( reverse('grad.views.view', kwargs={'grad_slug': grad_slug}) ))

        # search submit with non-slug redirects to "did you mean" page
        response = client.get(reverse('grad.views.quick_search')+'?search=0nnn')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['location'].endswith( reverse('grad.views.not_found')+"?search=0nnn" ))
        
        response = client.get(response['location'])
        gradlist = response.context['grads']
        self.assertEqual(len(gradlist), 1)
        self.assertEqual(gradlist[0], GradStudent.objects.get(person__userid='0nnngrad'))

    def test_that_grad_search_returns_200_ok(self):
        """
        Tests that /grad/search is available.
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('grad.views.search'))
        self.assertEqual(response.status_code, 200)
    
    def test_that_grad_search_with_csv_option_returns_csv(self):
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('grad.views.search'), {'columns':'person.first_name', 'csv':'sure'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_grad_pages(self):
        """
        Check overall pages for the grad module and make sure they all load
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        prog = GradProgram.objects.all()[0]
        GradRequirement(program=prog, description="Some Requirement").save()
        
        # search results
        url = reverse('grad.views.search', kwargs={}) + "?last_name_contains=Grad&columns=person.userid&columns=person.first_name"
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('grad/search_results.html', [t.name for t in response.templates])

        # other pages
        for view in ['search', 'programs', 'new_program', 'requirements', 'new_requirement',
                     'letter_templates', 'new_letter_template', 'manage_scholarshipType']:
            try:
                url = reverse('grad.views.'+view, kwargs={})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise



    def test_grad_student_pages(self):
        """
        Check the pages for a grad student and make sure they all load
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        gs = GradStudent.objects.get(person__userid='0nnngrad')
        sem = Semester.current()
        
        # put some data there so there's something to see in the tests (also, the empty <tbody>s don't validate)
        req = GradRequirement(program=gs.program, description="Some Requirement")
        req.save()
        st = ScholarshipType(unit=gs.program.unit, name="Some Scholarship")
        st.save()
        lt = LetterTemplate(unit=gs.program.unit, label='Template', content="This is the\n\nletter for {{first_name}}.")
        lt.save()
        Supervisor(student=gs, supervisor=Person.objects.get(userid='ggbaker'), supervisor_type='SEN').save()
        GradStatus(student=gs, status='ACTI', start=sem).save()
        CompletedRequirement(student=gs, requirement=req, semester=sem).save()
        Scholarship(student=gs, scholarship_type=st, amount=1000, start_semester=sem, end_semester=sem).save()
        OtherFunding(student=gs, amount=100, semester=sem, description="Some Other Funding", comments="Other Funding\n\nComment").save()
        Promise(student=gs, amount=10000, start_semester=sem, end_semester=sem.next_semester()).save()
        
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
        for view in ['financials', 'manage_general', 'manage_requirements', 'manage_scholarships', 'new_letter',
                      'manage_otherfunding', 'manage_promises', 'manage_letters', 'manage_status', 'manage_supervisors']:
            try:
                url = reverse('grad.views.'+view, kwargs={'grad_slug': gs.slug})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise
        
    def test_grad_letters(self):
        """
        Check handling of letters for grad students
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        gs = GradStudent.objects.get(person__userid='0nnngrad')

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
        
        
        
