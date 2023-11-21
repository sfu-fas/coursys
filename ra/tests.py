from django.test import TestCase
from courselib.testing import Client, test_views, freshen_roles
from ra.models import RAAppointment, RARequest, Account, Project, Unit, Person
from django.urls import reverse
from datetime import date


class RATest(TestCase):
    fixtures = ['basedata', 'coredata', 'ta_ra']

    def test_pages(self):
        """
        Test basic page rendering
        """
        freshen_roles()
        c = Client()
        c.login_user('dzhao')

        test_views(self, c, 'ra:', ['dashboard', 'new_request', 'browse'], {})

        ra = RAAppointment.objects.filter(unit__label='CMPT')[0]

        p = ra.person
        test_views(self, c, 'ra:', ['edit', 'view'], {'ra_slug': ra.slug})

        # No offer text yet, we should get a redirect when trying to edit the letter text:
        url = reverse('ra:edit_letter', kwargs={'ra_slug': ra.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 302)

        # Let's add some offer text and try again.
        ra.offer_letter_text='Some test text here'
        ra.save()
        test_views(self, c, 'ra:', ['edit_letter'], {'ra_slug': ra.slug})

        # Make sure we can add attachments
        test_views(self, c, 'ra:', ['new_attachment'], {'ra_slug': ra.slug})

        # NEW RA

        # test basic pages
        test_views(self, c, 'ra:', ['browse_appointments', 'new_request', 'dashboard', 'active_appointments', 'advanced_search'], {})
        # test search
        test_views(self, c, 'ra:', ['appointee_appointments', 'supervisor_appointments'], {'userid': p.userid})

        # create test rarequest
        u = Unit.objects.get(slug='cmpt')
        s = Person.objects.get(userid='dzhao')
        req = RARequest(person=p, unit=u, author=s, supervisor=s, config={}, hiring_category='RA', start_date=date(2021, 6, 1), end_date=date(2021, 9, 1), total_pay=1000)
        req.save()

        # test accounts
        test_views(self, c, 'ra:', ['new_account', 'accounts_index'], {})
        acct = Account.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra:', ['edit_account'], {'account_slug': acct.slug})

        # test pages associated with an rarequest
        test_views(self, c, 'ra:', ['view_request', 'edit_request', 'reappoint_request', 'edit_request_notes',
                                    'request_paf', 'request_offer_letter_update', 'new_admin_attachment'], {'ra_slug': req.slug})

