from datetime import date
from datetime import timedelta

from django.test import TestCase
from django.utils import safestring
from courselib.testing import Client, test_views, TEST_COURSE_SLUG

from coredata.models import Semester
from coredata.models import Person
from coredata.models import Role
from coredata.models import Unit

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.career import SalaryModificationEventHandler
from faculty.event_types.mixins import SalaryCareerEvent
from faculty.event_types.mixins import TeachingCareerEvent
from faculty.models import CareerEvent, TempGrant
from faculty.models import HANDLERS, EVENT_TYPES
from faculty.management.commands import faculty_test_data

import datetime


class EventTypesTest(TestCase):
    def setUp(self):
        faculty_test_data.Command().handle()

    def test_management_permissions(self):
        """
        Check that permission methods are returning as expected
        """
        fac_member = Person.objects.get(userid='ggbaker')
        dept_admin = Person.objects.get(userid='dixon')
        dean_admin = Person.objects.get(userid='dzhao')

        fac_role = Role.objects.filter(person=fac_member)[0]
        handler = SalaryModificationEventHandler(CareerEvent(person=fac_member,
                                                      unit=fac_role.unit))

        # tests below assume these permission settings for this event type
        self.assertEquals(handler.VIEWABLE_BY, 'MEMB')
        self.assertEquals(handler.EDITABLE_BY, 'DEPT')
        self.assertEquals(handler.APPROVAL_BY, 'FAC')

        self.assertFalse(handler.can_edit(fac_member))
        self.assertTrue(handler.can_edit(dept_admin))
        self.assertTrue(handler.can_edit(dean_admin))

        self.assertFalse(handler.can_approve(fac_member))
        self.assertFalse(handler.can_approve(dept_admin))
        self.assertTrue(handler.can_approve(dean_admin))

    def test_event_types(self):
        """
        Basic tests of each event handler
        """
        fac_member = Person.objects.get(userid='ggbaker')
        fac_role = Role.objects.filter(person=fac_member)[0]
        editor = Person.objects.get(userid='dixon')
        units = Unit.objects.all()
        start_date = datetime.date(2014, 1, 1)

        for Handler in HANDLERS:
            # Make sure all required abstract methods at least overrided
            # XXX: should output the missing method on fail
            try:
                # If a handler is missing any required methods (like teaching, salary, etc),
                # then instantiation will raise an Exception. This means that there is no need
                # to explicitly check if a handler with a flag has overriden a specific base
                # mixin method.
                handler = Handler(CareerEvent(person=fac_member,
                                              unit=fac_role.unit,
                                              start_date=start_date))
                handler.set_handler_specific_data()

                if 'affects_salary' in Handler.FLAGS:
                    self.assertTrue(issubclass(Handler, SalaryCareerEvent))
                    self.assertIsInstance(handler, SalaryCareerEvent)
                    self.assertIsInstance(handler.salary_adjust_annually(), SalaryAdjust)
                    self.assertTrue(handler.event.flags.affects_salary)
                else:
                    self.assertFalse(handler.event.flags.affects_salary)

                if 'affects_teaching' in Handler.FLAGS:
                    self.assertTrue(issubclass(Handler, TeachingCareerEvent))
                    self.assertIsInstance(handler, TeachingCareerEvent)
                    self.assertIsInstance(handler.teaching_adjust_per_semester(), TeachingAdjust)
                    self.assertTrue(handler.event.flags.affects_teaching)
                else:
                    self.assertFalse(handler.event.flags.affects_teaching)

                # test form creation
                Handler.get_entry_form(editor=editor, units=units)

                # display methods that each handler must implement
                shortsummary = handler.short_summary()
                self.assertIsInstance(shortsummary, basestring)
                self.assertNotIn('%s', shortsummary) # find these cases that shouldn't exist
                html = handler.to_html()
                self.assertIsInstance(html, (safestring.SafeString, safestring.SafeText, safestring.SafeUnicode))

            except:
                print "failure with Handler==%s" % (Handler)
                raise


class CareerEventHandlerBaseTest(TestCase):
    def setUp(self):
        faculty_test_data.Command().handle()

        class FoobarHandler(CareerEventHandlerBase):

            EVENT_TYPE = 'FOOBAR'
            NAME = 'Foo'

            def short_summary(self):
                return 'foobar'

        self.Handler = FoobarHandler
        self.person = Person.objects.get(userid='ggbaker')
        self.unit = Unit.objects.get(id=1)

        # XXX: Monkey-patch the test Handler into the global handler dict
        EVENT_TYPES['FOOBAR'] = FoobarHandler

    def tearDown(self):
        del EVENT_TYPES['FOOBAR']

    def test_is_instant(self):
        self.Handler.IS_INSTANT = True
        handler = self.Handler(CareerEvent(person=self.person,
                                           unit=self.unit))

        # Ensure the 'end_date' field is successfully removed
        form = handler.get_entry_form(self.person, [])
        self.assertNotIn('end_date', form.fields)

        # 'end_date' should be None before saving
        handler.event.start_date = date.today()
        self.assertIsNone(handler.event.end_date)

        # 'start_date' should be equal to 'end_date' after saving
        handler.save(self.person)
        self.assertEqual(handler.event.start_date, handler.event.end_date)

    def test_is_exclusive_close_previous(self):
        self.Handler.IS_EXCLUSIVE = True
        handler1 = self.Handler(CareerEvent(person=self.person,
                                            unit=self.unit))
        handler1.event.title = 'hello world'
        handler1.event.start_date = date.today()
        handler1.save(self.person)

        handler2 = self.Handler(CareerEvent(person=self.person,
                                            unit=self.unit))
        handler2.event.title = 'Foobar'
        handler2.event.start_date = date.today() + timedelta(days=1)
        handler2.save(self.person)

        # XXX: handler1's event won't be automatically refreshed after we've 'closed' it
        #      so we must grab a fresh copy to verify.
        handler1_modified_event = CareerEvent.objects.get(id=handler1.event.id)

        self.assertEqual(handler1_modified_event.end_date, handler2.event.start_date - datetime.timedelta(days=1))


class CareerEventTest(TestCase):
    def setUp(self):
        faculty_test_data.Command().handle()
        self.p = Person.objects.get(userid='ggbaker')
        self.u = Unit.objects.get(id=1)
        self.date = datetime.date(2014, 1, 1)
        self.e = CareerEvent(person=self.p, unit=self.u, event_type="APPOINT", start_date=self.date)
        self.e.save(self.p)

    def test_get_effective_date(self):
        events = CareerEvent.objects.effective_date(self.date)
        for e in events:
            assert e.start_date <= self.date
            assert e.end_date == None or e.end_date >= self.date
            
    def test_get_effective_semester(self):
        semester = Semester.objects.get(name='1141')
        events = CareerEvent.objects.effective_semester(semester)
        start, end = semester.start_end_dates(semester)
        for e in events:
            assert e.start_date >= start
            assert e.end_date == None or (e.end_date <= end and e.end_date >= start)


class PagesTest(TestCase):
    def setUp(self):
        faculty_test_data.Command().handle()

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()

        # as department admin
        c.login_user('dzhao')

        test_views(self, c, 'faculty.views.', ['index', 'search_index', 'salary_index', 'status_index', 'manage_event_index',
                'teaching_capacity', 'fallout_report', 'course_accreditation'],
                {})
        test_views(self, c, 'faculty.views.', ['summary', 'teaching_summary', 'salary_summary', 'otherinfo',
                'event_type_list', 'study_leave_credits', 'timeline', 'faculty_member_info', 'edit_faculty_member_info',
                'faculty_wizard'],
                {'userid': 'ggbaker'})
        test_views(self, c, 'faculty.views.', ['view_event', 'change_event', 'new_attachment'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position'})

        test_views(self, c, 'faculty.views.', ['manage_memo_template'],
                {'event_type': 'appoint', 'slug': 'cmpt-welcome'})
        test_views(self, c, 'faculty.views.', ['new_memo'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position',
                 'memo_template_slug': 'cmpt-welcome'})
        test_views(self, c, 'faculty.views.', ['manage_memo', 'view_memo'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position',
                 'memo_slug': '2000-appointment-to-position-welcome'})

        test_views(self, c, 'faculty.views.', ['teaching_credit_override'],
                {'userid': 'ggbaker', 'course_slug': TEST_COURSE_SLUG})
        test_views(self, c, 'faculty.views.', ['new_event_flag'],
                {'event_type': 'fellow'})

        # grant views
        test_views(self, c, 'faculty.views.', ['grant_index'], {})
        test_views(self, c, 'faculty.views.', ['convert_grant'],
                {'gid': TempGrant.objects.all()[0].id})
        test_views(self, c, 'faculty.views.', ['edit_grant', 'view_grant'],
                {'unit_slug': 'cmpt', 'grant_slug': 'baker-startup-grant'})

        # TODO: CSV views, JSON view

        # per-handler views
        for Handler in HANDLERS:
            try:
                slug = Handler.EVENT_TYPE.lower()

                test_views(self, c, 'faculty.views.', ['create_event'],
                    {'userid': 'ggbaker', 'event_type': slug})
                test_views(self, c, 'faculty.views.', ['memo_templates', 'new_memo_template'],
                    {'event_type': slug})

                # the search form
                test_views(self, c, 'faculty.views.', ['search_events'],
                    {'event_type': slug})
                # search with some results
                test_views(self, c, 'faculty.views.', ['search_events'],
                    {'event_type': slug}, qs='only_current=on')
            except:
                print "failure with Handler==%s" % (Handler)
                raise
