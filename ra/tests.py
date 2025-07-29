from django.test import TestCase
from courselib.testing import Client, test_views, freshen_roles
from ra.models import RAAppointment, RARequest, Account, Project, Unit, Person, Role
from django.urls import reverse
import datetime


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
        test_views(self, c, 'ra:', ['browse_appointments', 'new_request', 'dashboard', 'active_appointments', 'advanced_search', 'download_index'], {})
        # test search
        test_views(self, c, 'ra:', ['appointee_appointments', 'supervisor_appointments'], {'userid': p.userid})

        # create test rarequest
        unit = Unit.objects.get(slug='cmpt')
        supervisor = Person.objects.get(userid='ggbaker')
        admin = Person.objects.get(userid='dzhao')

        req = RARequest(person=p, unit=unit, author=supervisor, supervisor=supervisor, config={}, hiring_category='RA', start_date=datetime.date(2021, 6, 1), end_date=datetime.date(2021, 9, 1), draft=False, total_pay=1000)
        req.save()

        # test research assistants with FDMA
        r = Role(person=admin, role='FDMA', unit=unit, expiry=(datetime.date.today() + datetime.timedelta(days=5)))
        r.save()
        test_views(self, c, 'ra:', ['view_request', 'edit_request', 'reappoint_request', 'edit_request_notes',
                                    'request_paf', 'request_offer_letter_update', 'new_admin_attachment'], {'ra_slug': req.slug})
        r.delete()
        
        # test research assistants without FDMA
        url = reverse('ra:edit_request', kwargs={'ra_slug': req.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 404)
        url = reverse('ra:request_paf', kwargs={'ra_slug': req.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 404)
        url = reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # admin shouldn't be able to delete drafts that aren't theirs
        req.draft = True
        req.save()
        url = reverse('ra:delete_request_draft', kwargs={'ra_slug': req.slug})
        response = c.get(url)
        self.assertEqual(response.status_code, 404)
        req.draft = False
        req.save()

        # test non-continuing
        req.hiring_category = "NC"
        req.save()
        test_views(self, c, 'ra:', ['view_request', 'edit_request', 'reappoint_request', 'edit_request_notes',
                                    'request_paf', 'request_offer_letter_update', 'new_admin_attachment'], {'ra_slug': req.slug})
        
        # test graduate research assistant
        req.hiring_category = "GRAS"
        req.save()
        test_views(self, c, 'ra:', ['view_request', 'edit_request', 'reappoint_request', 'edit_request_notes',
                                    'request_paf', 'request_offer_letter_update', 'new_admin_attachment'], {'ra_slug': req.slug})

        # test accounts
        test_views(self, c, 'ra:', ['new_account', 'accounts_index'], {})
        acct = Account.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ra:', ['edit_account'], {'account_slug': acct.slug})

