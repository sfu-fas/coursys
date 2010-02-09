from django.test import TestCase
from submission.models import *
from grades.models import NumericActivity
from coredata.tests import create_offering

class SubmissionTest(TestCase):
    def setUp(self):
        pass

    def test_components(self):
        """
        Test submission component classes: subclasses, selection, sorting.
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15)
        a.save()
        
        c = URLComponent(activity=a, title="URL", position=8)
        c.save()
        c = ArchiveComponent(activity=a, title="Archive", position=1, max_size=100000)
        c.save()
        c = PlainTextComponent(activity=a, title="Text", position=89)
        c.save()
        c = CppComponent(activity=a, title="CPP", position=2)
        c.save()
        
        comps = AllComponents(a)
        self.assertEqual(len(comps), 4)
        self.assertEqual(comps[0].title, 'Archive') # make sure position=1 is first
        self.assertEqual(type(comps[1]), CppComponent)
        self.assertEqual(type(comps[3]), PlainTextComponent)


