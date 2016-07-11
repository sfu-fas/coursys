from courselib.testing import test_views, Client
from django.test import TestCase
from django.core.urlresolvers import reverse


class OutreachTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'outreach']


    def test_unaccessible_pages(self):
        client = Client()
        # First, without logging in:
        url = reverse('outreach_index')
        response = client.get(url)
        self.assertEquals(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('pba7')
        response = client.get(url)
        self.assertEquals(response.status_code, 403)


    def test_pages(self):
        client = Client()
        event_slug = 'cmpt-a-test-event-2016-06-23'
        event_registration_id = 1
        # Anyone should be able to register
        test_views(self, client, '', ['register', 'register_success'], {'event_slug': event_slug})

        # Log in as someone with the correct role.
        client.login_user('ggbaker')

        test_views(self, client, '', ['outreach_index', 'all_registrations'], {})
        test_views(self, client, '', ['edit_event', 'view_event', 'view_event_registrations'],
                   {'event_slug': event_slug})
        test_views(self, client, '', ['view_registration', 'edit_registration'],
                   {'registration_id': event_registration_id})

        url=reverse('toggle_registration_attendance', kwargs={'registration_id': event_registration_id})
        response = client.post(url, follow=True)
        self.assertEquals(response.status_code, 200)





