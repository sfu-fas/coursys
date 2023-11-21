from courselib.testing import test_views, Client, freshen_roles
from django.test import TestCase
from django.urls import reverse
from coredata.models import Unit, Role, Person
from space.models import BookingRecord
import datetime


class SpaceTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'space']

    today = datetime.date.today()
    long_start = today - datetime.timedelta(days=5 * 365)

    def setUp(self):
        freshen_roles()

    def test_inaccessible_pages(self):
        # Presumably, our booking that starts more than 5 years ago is the one generated in the fixtures.  If there are
        # others that old, it should at least be the first.
        unit = Unit.objects.get(slug='cmpt')
        booking = BookingRecord.objects.filter(start_time__lte=self.long_start, location__unit=unit).first()
        location = booking.location
        roomtype = location.room_type
        client = Client()
        # First, without logging in:
        url = reverse('space:index')
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('pba7')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

        # We darn well better not be able to delete anything without the proper role:
        url = reverse('space:delete_booking', kwargs={'booking_id': booking.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 403)

        url = reverse('space:delete_location', kwargs={'location_id': location.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 403)

        url = reverse('space:delete_roomtype', kwargs={'roomtype_id': roomtype.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_pages(self):
        # Presumably, our booking that starts more than 5 years ago is the one generated in the fixtures.  If there are
        # others that old, it should at least be the first.
        unit = Unit.objects.get(slug='cmpt')
        booking = BookingRecord.objects.filter(start_time__lte=self.long_start, location__unit=unit).first()
        location = booking.location
        roomtype = location.room_type
        client = Client()

        userid = Role.objects_fresh.filter(role='SPAC', unit=unit)[0].person.userid
        client.login_user(userid)
        test_views(self, client, 'space:', ['index', 'list_roomtypes', 'add_roomtype', 'manage_safety_items',
                                            'add_safety_item'], {})
        test_views(self, client, 'space:', ['view_location', 'edit_location', 'add_booking'],
                   {'location_slug': location.slug})
        test_views(self, client, 'space:', ['view_roomtype', 'edit_roomtype'], {'roomtype_slug': roomtype.slug})
        test_views(self, client, 'space:', ['view_booking', 'edit_booking', 'add_booking_attachment'],
                   {'booking_slug': booking.slug})

        # Now, we should be able to delete stuff properly.
        url = reverse('space:delete_booking', kwargs={'booking_id': booking.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)

        url = reverse('space:delete_location', kwargs={'location_id': location.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)

        url = reverse('space:delete_roomtype', kwargs={'roomtype_id': roomtype.id})
        response = client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
