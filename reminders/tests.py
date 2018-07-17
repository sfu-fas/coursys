from django.test import TestCase
from django.urls import reverse
from courselib.testing import Client, test_views
from coredata.models import Unit, Person
from reminders.models import Reminder, ReminderMessage
import datetime


class RemindersTest(TestCase):
    fixtures = ['basedata', 'coredata', 'reminders']

    def test_reminder_objects(self):
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
        test_views(self, c, 'reminders:', ['view', 'edit'], {'reminder_slug': rem.slug})

    def test_permissions(self):
        """
        Make sure the basic permission things are as-expected.
        """
        c = Client()

        # a role reminder: users with the role, but not others
        r = Reminder(reminder_type='ROLE', role='ADVS', unit=Unit.objects.get(slug='cmpt'),
                     date_type='SEM', week=4, weekday=0,
                     person=Person.objects.get(userid='ggbaker'), title='Advisor reminder', content='foo',)
        r.save()

        url = reverse('reminders:view', kwargs={'reminder_slug': r.slug})
        c.login_user('ggbaker')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 404)

        c.login_user('dzhao')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

        # a personal reminder: that person only
        r = Reminder(reminder_type='PERS',
                     date_type='YEAR', month='5', day=31,
                     person=Person.objects.get(userid='ggbaker'), title='Personal reminder',
                     content='### Heading\n\nfoo *bar*', config={'markup': 'markdown'})
        r.save()

        url = reverse('reminders:view', kwargs={'reminder_slug': r.slug})
        c.login_user('ggbaker')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

        c.login_user('dzhao')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 404)

        # test the HTML generation while we're here
        self.assertEqual(r.html_content().replace('\n', ''), '<h3>Heading</h3><p>foo <em>bar</em></p>')

    def _month_day_offset(self, offset):
        date = datetime.date.today() + datetime.timedelta(days=offset)
        return date.month, date.day

    def test_message_generation(self):
        """
        Make sure ReminderMessage objects are generated as expected.
        """
        kwargs = {'reminder_type': 'PERS', 'person': Person.objects.get(userid='ggbaker'),
                  'title': 'Test reminder', 'content': 'foo'}

        m, d = self._month_day_offset(3) # near future: remindermessage should generate
        r0 = Reminder(date_type='YEAR', month=m, day=d, **kwargs)
        r0.save()

        m, d = self._month_day_offset(-30) # distant past: remindermessage should not generate
        r1 = Reminder(date_type='YEAR', month=m, day=d, **kwargs)
        r1.save()

        m, d = self._month_day_offset(90) # far future: remindermessage should not generate
        r2 = Reminder(date_type='YEAR', month=m, day=d, **kwargs)
        r2.save()

        Reminder.create_all_reminder_messages()

        rms = list(ReminderMessage.objects.all())
        self.assertTrue(len(rms) >= 1) # may be other reminders from fixture objects, depending on run date
        rm = rms[0]
        self.assertEqual(rm.reminder, r0)
        self.assertEqual(rm.sent, False)
        ReminderMessage.send_all()
        self.assertEqual(rm.sent, False) # shouldn't send: still in the future
