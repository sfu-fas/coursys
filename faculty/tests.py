from django.test import TestCase

from coredata.models import Person, Unit, Role
from faculty.models import EVENT_TYPES
from event_types.career import AppointmentEventType

class EventTypesTest(TestCase):
    fixtures = ['faculty-test.json']

    def setUp(self):
        pass

    def test_event_types(self):
        fac_member = Person.objects.get(userid='ggbaker') 
        for EType in EVENT_TYPES.values():
            event_type = EType(fac_member)
            
            form = event_type.get_entry_form()
            #print form
            
