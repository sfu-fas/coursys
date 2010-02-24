"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from coredata.models import *
from grades.models import *
from models import *
from settings import CAS_SERVER_URL
from courselib.testing import *

class BasicTest(TestCase):
    fixtures = ['test_data']    
    
    def test_add_activity_components(self):
        c = CourseOffering.objects.get(slug = '1101-cmpt-165-d100')
       
        #add an numeric activity and its components
        a = NumericActivity(offering = c, name = 'assignment_1', \
                            short_name = 'a1', status = 'released', \
                            max_grade = 100, position = 0)
        a.save()
      
        co1 = ActivityComponent(numeric_activity = a, title = 'part1', max_mark = 20, position = 0)
        co2 = ActivityComponent(numeric_activity = a, title = 'part2', max_mark = 30, position = 1)
        co3 = ActivityComponent(numeric_activity = a, title = 'part3', max_mark = 50, position = 2)
        
        co1.save()
        co2.save()
        co3.save()
        
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)
        url = '/marking/1101-cmpt-165-d100/a1/components/';
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        #validate_content(self, response.content, 'activity components') ? error
          
        forms = response.context['formset'].forms
        self.assertEquals(forms[0].instance.title, 'part1')
        self.assertEquals(forms[1].instance.title, 'part2')
        self.assertEquals(forms[2].instance.title, 'part3') 
        
    def test_add_common_problems(self):
        c = CourseOffering.objects.get(slug = '1101-cmpt-165-d100')
        a = NumericActivity(offering = c, name = 'assignment_1', \
                            short_name = 'a1', status = 'released', \
                            max_grade = 100, position = 0)
        a.save()        
        co1 = ActivityComponent(numeric_activity = a, title = 'part1', max_mark = 50, position = 0)
        co2 = ActivityComponent(numeric_activity = a, title = 'part2', max_mark = 50, position = 1) 
        co1.save()
        co2.save()
        
        #add some common problems
        cp1 = CommonProblem(activity_component = co1, title = 'cp1')
        cp2 = CommonProblem(activity_component = co1, title = 'cp2')        
        cp3 = CommonProblem(activity_component = co2, title = 'cp3')
        
        cp1.save()
        cp2.save()
        cp3.save()
        
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)
        
        url = '/marking/1101-cmpt-165-d100/a1/common_problems/'
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
        forms = response.context['formset'].forms
 
        ins0 = forms[0].instance
        ins1 = forms[1].instance
        ins2 = forms[2].instance
        
        self.assertEquals(ins0.title, 'cp1')
        self.assertEquals(ins0.activity_component, co1)
        self.assertEquals(ins1.title, 'cp2')
        self.assertEquals(ins1.activity_component, co1)
        self.assertEquals(ins2.title, 'cp3')
        self.assertEquals(ins2.activity_component, co2)
        
        #test the marking page as well
        url = '/marking/1101-cmpt-165-d100/a1/marking/'
        response = self.client.get(url)
        
        mark_components = response.context['mark_components']
        com1 = mark_components[0]
        com2 = mark_components[1]
        
        self.assertEquals(com1['component'], co1)
        self.assertEquals(len(com1['common_problems']), 2)
        self.assertEquals(com2['component'], co2)
        self.assertEquals(len(com2['common_problems']), 1)
           
        