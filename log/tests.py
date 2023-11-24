from django.test import TestCase
from django.urls import reverse

from courselib.testing import Client, test_views
from courses import settings
from log.forms import EVENT_FORM_TYPES, EventLogFilterForm
from log.models import EventLogEntry, RequestLog, EVENT_LOG_TYPES, CeleryTaskLog
from log.views import EVENT_DATA_VIEWS


class EventLogEntryTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_code_coherence(self):
        """
        Make sure the various EventLogEntry discovery stuff is coherent.
        """
        self.assertEqual(set(EVENT_LOG_TYPES.keys()), set(EVENT_FORM_TYPES.keys()))
        self.assertEqual(set(EVENT_LOG_TYPES.keys()), set(EVENT_DATA_VIEWS.keys()))

        # EVENT_LOG_TYPES: map of type to model subclass
        for cls in EVENT_LOG_TYPES.values():
            self.assertTrue(issubclass(cls, EventLogEntry))

        # EVENT_FORM_TYPES: map of type to filtering form
        for cls in EVENT_FORM_TYPES.values():
            self.assertTrue(issubclass(cls, EventLogFilterForm))

        # EVENT_DATA_VIEWS: map of type to data view
        for t, cls in EVENT_DATA_VIEWS.items():
            self.assertEqual(cls.model, EVENT_LOG_TYPES[t])
            self.assertEqual(cls.columns, EVENT_LOG_TYPES[t].display_columns)

    def test_requestlog_creation(self):
        """
        Check that various requests cause appropriate RequestLog object creation.

        Is .order_by('-time').first() sufficiently stable to trust to get the correct RequestLog here? Hopefully yes.
        """
        c = Client()

        url = reverse('browse:browse_courses')
        response = c.get(url)
        log = RequestLog.objects.order_by('-time').first()
        self.assertEqual(log.username, None)
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.path, url)
        self.assertEqual(log.data['ip'], '127.0.0.1')
        self.assertEqual(log.data['status_code'], 200)

        c.login_user('ggbaker')
        response = c.get('/')
        log = RequestLog.objects.order_by('-time').first()
        self.assertEqual(log.username, 'ggbaker')

        response = c.get('/page_that_doesnt_exist')
        log = RequestLog.objects.order_by('-time').first()
        self.assertEqual(log.data['status_code'], 404)

        url = reverse('sysadmin:admin_panel')
        with self.assertRaises(RuntimeError):
            response = c.get(url + '?content=throw')
        log = RequestLog.objects.order_by('-time').first()
        self.assertEqual(log.data['status_code'], 500)
        self.assertIn('exception', log.data)

    def test_celerytasklog_creation(self):
        """
        If possible, test logging of celery tasks.
        """
        if not settings.USE_CELERY:
            return
        from coredata.tasks import ping, failing_task

        res = ping.apply()
        res.get(timeout=5)
        log = CeleryTaskLog.objects.order_by('-time').first()
        self.assertEqual(log.task, 'coredata.tasks.ping')

        with self.assertRaises(RuntimeError):
            res = failing_task.apply()
            res.get(timeout=5)
        log = CeleryTaskLog.objects.order_by('-time').first()
        self.assertEqual(log.task, 'coredata.tasks.failing_task')
        self.assertEqual(log.data['exception'], 'RuntimeError')

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()
        c.login_user('dzhao')
        response = c.get(reverse('sysadmin:log_explore'))
        self.assertEqual(response.status_code, 403)

        c.login_user('ggbaker')
        test_views(self, c, 'sysadmin:', ['log_explore'], {})
