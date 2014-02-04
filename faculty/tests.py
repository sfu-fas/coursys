from datetime import date
from datetime import timedelta

from django.test import TestCase
from django.utils import safestring

from coredata.models import Person
from coredata.models import Role
from coredata.models import Unit

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.career import AppointmentEventHandler
from faculty.event_types.mixins import SalaryCareerEvent
from faculty.event_types.mixins import TeachingCareerEvent
from faculty.models import CareerEvent
from faculty.models import HANDLERS

import datetime

class EventTypesTest(TestCase):
    fixtures = ['faculty-test.json']

    def setUp(self):
        pass

    def test_management_permissions(self):
        """
        Check that permission methods are returning as expected
        """
        fac_member = Person.objects.get(userid='ggbaker')
        dept_admin = Person.objects.get(userid='dixon')
        dean_admin = Person.objects.get(userid='dzhao')

        fac_role = Role.objects.filter(person=fac_member)[0]
        handler = AppointmentEventHandler.create_for(fac_member, fac_role.unit)

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

        for Handler in HANDLERS:
            # Make sure all required abstract methods at least overrided
            # XXX: should output the missing method on fail
            try:
                # If a handler is missing any required methods (like teaching, salary, etc),
                # then instantiation will raise an Exception. This means that there is no need
                # to explicitly check if a handler with a flag has overriden a specific base
                # mixin method.
                handler = Handler.create_for(fac_member, fac_role.unit)

                if 'affects_salary' in Handler.FLAGS:
                    self.assertTrue(issubclass(Handler, SalaryCareerEvent))
                    self.assertIsInstance(handler, SalaryCareerEvent)
                    self.assertIsInstance(handler.salary_adjust_annually(), SalaryAdjust)

                if 'affects_teaching' in Handler.FLAGS:
                    self.assertTrue(issubclass(Handler, TeachingCareerEvent))
                    self.assertIsInstance(handler, TeachingCareerEvent)
                    self.assertIsInstance(handler.teaching_adjust_per_semester(), TeachingAdjust)

                # test form creation
                handler.get_entry_form(editor=editor, units=units)

                # display methods that each handler must implement
                self.assertIsInstance(handler.short_summary(), basestring)
                html = handler.to_html()
                self.assertIsInstance(html, (safestring.SafeString, safestring.SafeText, safestring.SafeUnicode))


            except:
                print "failure with Handler==%s" % (Handler)
                raise


class CareerEventHandlerBaseTest(TestCase):
    fixtures = ['faculty-test.json']

    def setUp(self):
        class FoobarHandler(CareerEventHandlerBase):

            EVENT_TYPE = 'FOOBAR'
            NAME = 'Foo'

            def short_summary(self):
                return 'foobar'

        self.Handler = FoobarHandler
        self.person = Person.objects.get(userid='ggbaker')
        self.unit = Unit.objects.get(id=1)

    def test_is_instant(self):
        self.Handler.IS_INSTANT = True
        handler = self.Handler.create_for(self.person, self.unit)

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
        handler1 = self.Handler.create_for(self.person, self.unit)
        handler1.event.title = 'hello world'
        handler1.event.start_date = date.today()
        handler1.save(self.person)

        handler2 = self.Handler.create_for(self.person, self.unit)
        handler2.event.title = 'Foobar'
        handler2.event.start_date = date.today() + timedelta(days=1)
        handler2.save(self.person)

        # XXX: handler1's event won't be automatically refreshed after we've 'closed' it
        #      so we must grab a fresh copy to verify.
        handler1_modified_event = CareerEvent.objects.get(id=handler1.event.id)

        self.assertEqual(handler1_modified_event.end_date, handler2.event.start_date - datetime.timedelta(days=1))
