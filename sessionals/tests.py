from courselib.testing import test_views, Client
from django.test import TestCase
from django.core.urlresolvers import reverse

class SessionalTestCase(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_inaccessible_pages(self):
        client = Client()
        url = reverse('sessionals:sessionals_index')
        response = client.get(url)
        self.assertEquals(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('pba7')
        response = client.get(url)
        self.assertEquals(response.status_code, 403)

    def test_pages(self):
        client = Client()

        # as instructor
        client.login_user('dzhao')
        test_views(self, client, 'sessionals:', ['sessionals_index', 'manage_accounts', 'new_account', 'manage_configs',
                                                 'new_config'], {})
