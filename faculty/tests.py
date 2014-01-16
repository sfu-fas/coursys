from django.test import TestCase

from coredata.models import Person, Unit, Role
from faculty.models import EVENT_TYPES
from event_types.career import AppointmentEventType

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

        event_type = AppointmentEventType(fac_member)
        # tests below assume these permission settings for this event type
        self.assertEquals(event_type.editable_by, 'DEPT')
        self.assertEquals(event_type.approval_by, 'FAC')

        self.assertFalse(event_type.can_edit(fac_member))
        self.assertTrue(event_type.can_edit(dept_admin))
        self.assertTrue(event_type.can_edit(dean_admin))

        self.assertFalse(event_type.can_approve(fac_member))
        self.assertFalse(event_type.can_approve(dept_admin))
        self.assertTrue(event_type.can_approve(dean_admin))


    def test_event_types(self):
        """
        Basic tests of each event type
        """
        fac_member = Person.objects.get(userid='ggbaker')
        for EType in EVENT_TYPES.values():
            event_type = EType(fac_member)
            
            # test form creation
            form = event_type.get_entry_form()
            
            #print form
            #car_event = event_type.to_career_event(form)
            
