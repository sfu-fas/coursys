
from datetime import datetime
from django.test import TestCase
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