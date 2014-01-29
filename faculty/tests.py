from django.test import TestCase

from coredata.models import Person
from coredata.models import Role
from coredata.models import Unit

from faculty.event_types.career import AppointmentEventHandler
from faculty.event_types.mixins import SalaryCareerEvent
from faculty.event_types.mixins import TeachingCareerEvent
from faculty.models import HANDLERS


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
                handler = Handler.create_for(fac_member, fac_role.unit)
            except TypeError:
                self.fail('something was not implemented')

            # Make sure certain handlers subclassed from the appropriate mixin
            if 'affects_salary' in Handler.FLAGS:
                self.assertTrue(issubclass(Handler, SalaryCareerEvent))

            if 'affects_teaching' in Handler.FLAGS:
                self.assertTrue(issubclass(Handler, TeachingCareerEvent))

            # test form creation
            handler.get_entry_form(editor=editor, units=units)
