from django.test import TestCase
from django.test.client import Client
from submission.models import *
from grades.models import NumericActivity
from coredata.tests import create_offering
from settings import CAS_SERVER_URL
from coredata.models import *

class SubmissionTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        pass

    def test_components(self):
        """
        Test submission component classes: subclasses, selection, sorting.
        """
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, due_date="2010-03-01")
        a.save()
        
        c = URLComponent(activity=a, title="URL", position=8)
        c.save()
        c = ArchiveComponent(activity=a, title="Archive", position=1, max_size=100000)
        c.save()
        c = PlainTextComponent(activity=a, title="Text", position=89)
        c.save()
        c = CppComponent(activity=a, title="CPP", position=2)
        c.save()
        
        comps = select_all_components(a)
        self.assertEqual(len(comps), 4)
        self.assertEqual(comps[0].title, 'Archive') # make sure position=1 is first
        self.assertEqual(type(comps[1]), CppComponent)
        self.assertEqual(type(comps[3]), PlainTextComponent)

    def test_component_view_page(self):
        s, c = create_offering()
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, due_date="2010-03-01")
        a.save()
        p = Person.objects.get(userid="ggbaker")
        m = Member(person=p, offering=c, role="INST", career="NONS", added_reason="UNK")
        m.save()

        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        # When no component, should display error message
        response = client.get("/submission" + c.get_absolute_url()+"a1/")
        self.assertContains(response, "No component found")
        
        #add component and test
        component = URLComponent(activity=a, title="URLComponent")
        component.save()
        component = ArchiveComponent(activity=a, title="ArchiveComponent")
        component.save()
        component = CppComponent(activity=a, title="CppComponent")
        component.save()
        component = PlainTextComponent(activity=a, title="PlainTextComponent")
        component.save()
        component = JavaComponent(activity=a, title="JavaComponent")
        component.save()
        #should all appear
        response = client.response = client.get("/submission" + c.get_absolute_url()+"a1/")
        self.assertContains(response, "URLComponent")
        self.assertContains(response, "ArchiveComponent")
        self.assertContains(response, "CppComponent")
        self.assertContains(response, "PlainTextComponent")
        self.assertContains(response, "JavaComponent")
        #make sure type displays
        self.assertContains(response, '<li class="view"><label>Type:</label>Archive</li>')

        #delete component and test
        component.delete()
        response = client.response = client.get("/submission" + c.get_absolute_url()+"a1/")
        self.assertNotContains(response, "JavaComponent")

        
