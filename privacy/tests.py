from django.test import TestCase
from django.urls import reverse
from courselib.testing import basic_page_tests, Client, freshen_roles

from coredata.models import Person

class PrivacyTestCase(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_workflow(self):
        """
        Test the privacy policy workflow and page exclusions
        """
        freshen_roles()
        # clear privacy agreement from test data
        p = Person.objects.get(userid='dzhao')
        p.config = {}
        p.save()

        client = Client()
        client.login_user(p.userid)
        privacy_url = reverse('config:privacy')
        privacy_da_url = reverse('config:privacy_da')

        # non-role page should still render
        url = reverse('dashboard:index')
        basic_page_tests(self, client, url)

        # but role page should redirect to agreement
        url = reverse('advising:advising')
        response = client.get(url)
        self.assertRedirects(response, privacy_url + '?next=' + url)

        # check privacy page
        basic_page_tests(self, client, privacy_url)

        # submit and expect recorded agreement
        response = client.post(privacy_url + '?next=' + url, {'agree': 'on'})

        # You should get redirected again to the DA agreement...
        self.assertRedirects(response, url, target_status_code=302)

        p = Person.objects.get(userid='dzhao')
        self.assertTrue(p.config['privacy_signed'])
        response = client.get(url)
        self.assertRedirects(response, privacy_da_url + '?next=' + url)
        response = client.post(privacy_da_url + '?next=' + url, {'agree': 'on'})
        self.assertRedirects(response, url)
        p = Person.objects.get(userid='dzhao')
        self.assertTrue(p.config['privacy_da_signed'])
        # now we should be able to access
        basic_page_tests(self, client, url)


