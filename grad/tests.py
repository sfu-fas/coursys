from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
import json
from grad.models import GradStudent

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
        self.assertTrue(response['location'].endswith( reverse('grad.views.view_all', kwargs={'grad_slug': grad_slug}) ))

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
