from courselib.testing import test_views, Client, freshen_roles
from django.test import TestCase
from django.urls import reverse
from outreach.models import OutreachEvent, OutreachEventRegistration
from coredata.models import Unit, Role
import datetime


class OutreachTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'outreach']

    def test_inaccessible_pages(self):
        freshen_roles()
        client = Client()
        # First, without logging in:
        url = reverse('outreach:outreach_index')
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('pba7')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_pages(self):
        freshen_roles()
        client = Client()
        today = datetime.date.today()
        long_start = today + datetime.timedelta(days=5*365)
        # Our test even is probably the only one that starts at least 5 years from whatever day it is when we run this
        event = OutreachEvent.objects.current([Unit.objects.get(slug='cmpt')]).filter(start_date__gt=long_start).first()
        registration = OutreachEventRegistration.objects.filter(event=event).first()
        # Anyone should be able to register
        test_views(self, client, 'outreach:', ['register', 'register_success'], {'event_slug': event.slug})

        # Log in as someone with the correct role.
        userid = Role.objects_fresh.filter(role='OUTR', unit=Unit.objects.get(slug='cmpt'))[0].person.userid
        client.login_user(userid)
        test_views(self, client, 'outreach:', ['outreach_index', 'view_all_registrations'], {})
        test_views(self, client, 'outreach:', ['edit_event', 'view_event', 'view_event_registrations'],
                   {'event_slug': event.slug})
        test_views(self, client, 'outreach:', ['view_registration', 'edit_registration'],
                   {'registration_id': registration.id})

        url=reverse('outreach:toggle_registration_attendance', kwargs={'registration_id': registration.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
