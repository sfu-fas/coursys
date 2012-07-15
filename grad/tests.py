from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
import json, datetime
from grad.models import GradStudent, GradRequirement, GradProgram, Letter, LetterTemplate
from courselib.testing import basic_page_tests


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
        
        GradRequirement(program=gs.program, description="Some Requirement").save()
        
        url = reverse('grad.views.view', kwargs={'grad_slug': gs.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        for section in ['general', 'committee', 'status', 'requirements', 'scholarships', 'otherfunding', 'promises', 'letters']:
            # sections of the main gradstudent view that can be loaded
            url = reverse('grad.views.view', kwargs={'grad_slug': gs.slug})
            try:
                # don't check validity since they're page fragments. TODO: force them into the page somehow and check that
                response = client.get(url, {'section': section})
                self.assertEqual(response.status_code, 200)
            except:
                print "with section==" + repr(section)
                raise
            
        for view in ['financials', 'manage_academics', 'manage_requirements', 'manage_scholarship', 'new_letter']:
            # other pages for that student
            try:
                url = reverse('grad.views.'+view, kwargs={'grad_slug': gs.slug})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise

        for view in ['manage_supervisors', 'manage_status', 'view_all_letters', ]: # 'manage_otherfunding', 'manage_promises'
            # other pages for that student that aren't yet valid, but should be.
            try:
                url = reverse('grad.views.'+view, kwargs={'grad_slug': gs.slug})
                response = client.get(url)
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
        
        
        
