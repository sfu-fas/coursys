from datetime import date
from datetime import timedelta

from django.test import TestCase
from django.utils import safestring
from django.core.urlresolvers import reverse
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
        self.assertEqual(handler.VIEWABLE_BY, 'MEMB')
        self.assertEqual(handler.EDITABLE_BY, 'DEPT')
        self.assertEqual(handler.APPROVAL_BY, 'FAC')

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
                else:
                    self.assertFalse(handler.event.flags.affects_salary)

                if 'affects_teaching' in Handler.FLAGS:
                    self.assertTrue(issubclass(Handler, TeachingCareerEvent))
                    self.assertIsInstance(handler, TeachingCareerEvent)
                    self.assertIsInstance(handler.teaching_adjust_per_semester(), TeachingAdjust)
                else:
                    self.assertFalse(handler.event.flags.affects_teaching)

                # test form creation
                Handler.get_entry_form(editor=editor, units=units)

                # display methods that each handler must implement
                shortsummary = handler.short_summary()
                self.assertIsInstance(shortsummary, str)
                self.assertNotIn('%s', shortsummary) # find these cases that shouldn't exist
                html = handler.to_html()
                self.assertIsInstance(html, (safestring.SafeString, safestring.SafeText, safestring.SafeUnicode))

            except:
                print("failure with Handler==%s" % (Handler))
                raise

    def test_annual_teaching(self):
        """
        Test the annual teaching value entry field
        """
        person = Person.objects.get(userid='ggbaker')
        unit = Unit.objects.get(slug='cmpt')
        editor = Person.objects.get(userid='dzhao')
        etype = 'NORM_TEACH'
        event = CareerEvent.objects.filter(unit=unit, person=person, event_type=etype)[0]
        event.config['load'] = 2 # 2 courses/semester in database should be 6/year to the user
        event.get_handler().save(editor)

        c = Client()
        c.login_user(editor.userid)

        # make sure the form renders with value="6"
        url = reverse('faculty:change_event', kwargs={'userid': person.userid, 'event_slug': event.slug})
        resp = c.get(url)
        inputs = [l for l in resp.content.split('\n') if 'name="load"' in l]
        inputs_correct_value = [l for l in inputs if 'value="6"' in l]
        self.assertEqual(len(inputs_correct_value), 1)

        # POST a change and make sure the right value ends up in the DB
        data = {
            'start_date_0': '2000-09-01',
            'end_date_0': '',
            'unit': str(unit.id),
            'load': '5',
            'comments': '',
        }
        c.post(url, data)
        new_ce = CareerEvent.objects.filter(unit=unit, person=person, event_type=etype)[0]
        self.assertEqual(new_ce.config['load'], '5/3')




class CareerEventHandlerBaseTest(TestCase):
    def setUp(self):
        faculty_test_data.Command().handle()

        class FoobarHandler(CareerEventHandlerBase):

            EVENT_TYPE = 'FOOBAR'
            NAME = 'Foo'

            def short_summary(self):
                return 'foobar'

        class FoobarHandlerInstant(FoobarHandler):
            IS_INSTANT = True

        self.Handler = FoobarHandler
        self.HandlerInstant = FoobarHandlerInstant
        self.person = Person.objects.get(userid='ggbaker')
        self.unit = Unit.objects.get(id=1)

        # XXX: Monkey-patch the test Handler into the global handler dict
        EVENT_TYPES['FOOBAR'] = FoobarHandler

    def tearDown(self):
        del EVENT_TYPES['FOOBAR']

    def test_is_instant(self):
        handler = self.HandlerInstant(CareerEvent(person=self.person,
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
        self.e.get_handler().save(self.p)

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

    def test_flag_logic(self):
        """
        Check the event.flags setting logic: flags set only if there's a real effect.
        """
        e = CareerEvent(person=self.p, unit=self.u, event_type="FELLOW", start_date=self.date)
        e.config = {'add_salary': 0, 'add_pay': 0, 'teaching_credit': 0}
        h = e.get_handler()
        h.save(self.p)
        self.assertFalse(e.flags.affects_salary)
        self.assertFalse(e.flags.affects_teaching)

        e.config['add_salary'] = 5
        h.save(self.p)
        self.assertTrue(e.flags.affects_salary)
        self.assertFalse(e.flags.affects_teaching)

        e.config['add_salary'] = 0
        e.config['teaching_credit'] = 1
        h.save(self.p)
        self.assertFalse(e.flags.affects_salary)
        self.assertTrue(e.flags.affects_teaching)




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

        test_views(self, c, 'faculty:', ['index', 'search_index', 'salary_index', 'status_index', 'manage_event_index',
                'teaching_capacity', 'fallout_report', 'course_accreditation', 'manage_faculty_roles'],
                {})
        test_views(self, c, 'faculty:', ['summary', 'teaching_summary', 'salary_summary', 'otherinfo',
                'event_type_list', 'study_leave_credits', 'timeline', 'faculty_member_info', 'edit_faculty_member_info',
                'faculty_wizard'],
                {'userid': 'ggbaker'})
        test_views(self, c, 'faculty:', ['view_event', 'change_event', 'new_attachment', 'new_text_attachment',
                                               'new_memo_no_template'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position'})

        test_views(self, c, 'faculty:', ['manage_memo_template'],
                {'event_type': 'appoint', 'slug': 'cmpt-welcome'})
        test_views(self, c, 'faculty:', ['new_memo'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position',
                 'memo_template_slug': 'cmpt-welcome'})
        test_views(self, c, 'faculty:', ['manage_memo', 'view_memo'],
                {'userid': 'ggbaker', 'event_slug': '2000-appointment-to-position',
                 'memo_slug': '2000-appointment-to-position-welcome'})

        test_views(self, c, 'faculty:', ['teaching_credit_override'],
                {'userid': 'ggbaker', 'course_slug': TEST_COURSE_SLUG})
        test_views(self, c, 'faculty:', ['event_config_add'],
                {'event_type': 'fellow'})

        # grant views
        test_views(self, c, 'faculty:', ['grant_index'], {})
        test_views(self, c, 'faculty:', ['convert_grant'],
                {'gid': TempGrant.objects.all()[0].id})
        test_views(self, c, 'faculty:', ['edit_grant', 'view_grant'],
                {'unit_slug': 'cmpt', 'grant_slug': 'baker-startup-grant'})

        # TODO: CSV views, JSON view

        # per-handler views
        for Handler in HANDLERS:
            try:
                slug = Handler.EVENT_TYPE.lower()

                test_views(self, c, 'faculty:', ['create_event'],
                    {'userid': 'ggbaker', 'event_type': slug})
                test_views(self, c, 'faculty:', ['event_config', 'new_memo_template'],
                    {'event_type': slug})

                # the search form
                test_views(self, c, 'faculty:', ['search_events'],
                    {'event_type': slug})
                # search with some results
                test_views(self, c, 'faculty:', ['search_events'],
                    {'event_type': slug}, qs='only_current=on')
            except:
                print("failure with Handler==%s" % (Handler))
                raise
