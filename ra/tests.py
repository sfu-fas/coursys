from django.test import TestCase
from courselib.testing import Client, test_views
from ra.models import RAAppointment, Account, Project
from django.core.urlresolvers import reverse


class RATest(TestCase):
    fixtures = ['basedata', 'coredata', 'ta_ra']

    def test_pages(self):
        """
        Test basic page rendering
        """
        c = Client()
        c.login_user('dzhao')

        test_views(self, c, 'ra:', ['search', 'new', 'accounts_index', 'new_account', 'projects_index',
                                          'new_project', 'semester_config', 'browse'], {})
        test_views(self, c, 'ra:', ['found'], {}, qs='search=grad')

        ra = RAAppointment.objects.filter(unit__label='CMPT')[0]
        p = ra.person
        test_views(self, c, 'ra:', ['student_appointments', 'new_student'], {'userid': p.userid})
        test_views(self, c, 'ra:', ['edit', 'reappoint', 'view',], {'ra_slug': ra.slug})

        # No offer text yet, we should get a redirect when trying to edit the letter text:
        url = reverse('ra:edit_letter', kwargs={'ra_slug': ra.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 302)

        # Let's add some offer text and try again.
        ra.offer_letter_text='Some test text here'
        ra.save()
        test_views(self, c, 'ra:', ['edit_letter'], {'ra_slug': ra.slug})

        acct = Account.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra:', ['edit_account'], {'account_slug': acct.slug})

        proj = Project.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra:', ['edit_project'], {'project_slug': proj.slug})



