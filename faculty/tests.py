from django.test import TestCase
from django.utils import safestring

from coredata.models import Person, Unit, Role
from faculty.models import EVENT_TYPES
from event_types.base import SalaryAdjust, TeachingAdjust
from event_types.career import AppointmentEventHandler

import decimal

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

        handler = AppointmentEventHandler(faculty=fac_member)
        # tests below assume these permission settings for this event type
        self.assertEquals(handler.viewable_by, 'MEMB')
        self.assertEquals(handler.editable_by, 'DEPT')
        self.assertEquals(handler.approval_by, 'FAC')

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
        for Handler in EVENT_TYPES.values():
            try:
                handler = Handler(faculty=fac_member)

                # test salary/teaching calculation sanity
                if handler.affects_teaching:
                    # if this affects teaching, get_teaching_balance must be implemented
                    t = handler.teaching_adjust_per_semester()
                    self.assertIsInstance(t, TeachingAdjust)
                else:
                    # if not, it can't expect it do be called.
                    with self.assertRaises(NotImplementedError):
                        handler.teaching_adjust_per_semester()

                if handler.affects_salary:
                    # if this affects teaching, get_salary must be implemented
                    s = handler.salary_adjust_annually()
                    self.assertIsInstance(s, SalaryAdjust)
                else:
                    # if not, it can't expect it do be called.
                    with self.assertRaises(NotImplementedError):
                        handler.salary_adjust_annually()

                self.assertIsInstance(handler.default_title, basestring)
                self.assertIsInstance(handler.name, basestring)

                # test form creation
                form = handler.get_entry_form()

                # tests that I think should probably work eventually...
                #event = handler.load_form(form)
                #handler = Handler(event=event)
                self.assertIsInstance(handler.short_summary(), basestring)
                html = handler.to_html()
                self.assertIsInstance(html, (safestring.SafeString, safestring.SafeText, safestring.SafeUnicode))


            except:
                print "raising with event handler %s" % (Handler)
                raise
            
