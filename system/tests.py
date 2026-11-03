
from datetime import datetime
from django.test import TestCase
from django.urls import reverse
from system.models import SystemVariable
from courselib.testing import Client, freshen_roles, test_views

class SystemVariableTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_pages(self):
        """
        Test basic page rendering
        """

        freshen_roles()
        c = Client()
        c.login_user('ggbaker')

        test_views(self, c, 'system:', ['list_systemvariables', 'new_systemvariable'], {})

        systemvar = SystemVariable.objects.create(key='minimum_wage', label='Minimum Wage', value_type=SystemVariable.TYPE_DECIMAL, value='18.25', unit=None)

        test_views(self, c, 'system:', ['edit_systemvariable'], {'systemvariable_id': systemvar.pk})

    def test_delete_systemvariable_requires_post(self):
        freshen_roles()
        c = Client()
        c.login_user('ggbaker')
        systemvar = SystemVariable.objects.create(
            key='minimum_wage',
            label='Minimum Wage',
            value_type=SystemVariable.TYPE_DECIMAL,
            value='18.25',
            unit=None,
        )
        delete_url = reverse('system:delete_systemvariable', kwargs={
            'systemvariable_id': systemvar.pk,
        })

        response = c.get(delete_url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(SystemVariable.objects.filter(pk=systemvar.pk).exists())

        response = c.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SystemVariable.objects.filter(pk=systemvar.pk).exists())