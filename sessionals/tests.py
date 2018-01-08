from courselib.testing import test_views, Client
from django.test import TestCase
from django.core.urlresolvers import reverse
from sessionals.models import SessionalContract

class SessionalTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'sessionals']

    def test_inaccessible_pages(self):
        client = Client()
        contract_id = 1
        url = reverse('sessionals:sessionals_index')
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('foo')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
        url = reverse('sessionals:delete_contract', kwargs={'contract_id': contract_id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_pages(self):
        client = Client()
        account_slug = 'cmpt-234-sfufa-account'
        contract_slug = 'a-test-sessionalcontract'
        contract = SessionalContract.objects.get(slug=contract_slug)
        contract_id = contract.id
        # as instructor
        client.login_user('dzhao')
        test_views(self, client, 'sessionals:', ['sessionals_index', 'manage_accounts', 'new_account', 'manage_configs',
                                                 'new_config', 'new_contract'], {})
        test_views(self, client, 'sessionals:', ['edit_account', 'view_account'], {'account_slug': account_slug})
        test_views(self, client, 'sessionals:', ['view_contract', 'edit_contract'], {'contract_slug': contract_slug})
        url = reverse('sessionals:delete_contract', kwargs={'contract_id': contract_id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
