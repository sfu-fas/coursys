from django.test import TestCase
from courselib.testing import Client, test_views
from reminders.models import Reminder


class RemindersTest(TestCase):
    fixtures = ['basedata', 'coredata', 'reminders']

    def test_reminder_basics(self):
        rems = Reminder.objects.all()
        self.assertFalse([r for r in rems if r.status == 'D'], 'Reminder.objects returned deleted items')

        rems = Reminder.all_objects.all()
        self.assertTrue([r for r in rems if r.status == 'D'], 'Reminder.all_objects did not return deleted items')

    def test_pages(self):
        """
        Test basic page rendering
        """
        c = Client()
        c.login_user('ggbaker')

        test_views(self, c, 'reminders:', ['index', 'create'], {})
        rem = Reminder.objects.first()
        test_views(self, c, 'reminders:', ['view'], {'reminder_slug': rem.slug})
