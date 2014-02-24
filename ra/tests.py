from django.test import TestCase
from courselib.testing import Client, test_views
from ra.models import RAAppointment, Account, Project

class RATest(TestCase):
    fixtures = ['test_data']
    def test_pages(self):
        """
        Test basic page rendering
        """
        c = Client()
        c.login_user('ggbaker')

        test_views(self, c, 'ra.views.', ['search', 'new', 'accounts_index', 'new_account', 'projects_index',
                                          'new_project', 'semester_config', 'browse'], {})
        test_views(self, c, 'ra.views.', ['found'], {}, qs='search=grad')

        ra = RAAppointment.objects.filter(unit__label='CMPT')[0]
        p = ra.person
        test_views(self, c, 'ra.views.', ['student_appointments', 'new_student'], {'userid': p.userid})
        test_views(self, c, 'ra.views.', ['edit', 'reappoint', 'edit_letter', 'view',], {'ra_slug': ra.slug})

        acct = Account.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra.views.', ['edit_account'], {'account_slug': acct.slug})

        proj = Project.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra.views.', ['edit_project'], {'project_slug': proj.slug})



