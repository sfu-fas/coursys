"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.client import Client
from coredata.models import *
from grades.models import *
from models import *
from views import manage_activity_components, manage_common_problems, marking_student
from settings import CAS_SERVER_URL
from courselib.testing import *
from datetime import *
from django.core.urlresolvers import reverse
import decimal


class BasicTest(TestCase):
    fixtures = ['test_data']    
    def setUp(self):
        self.c_slug = '1101-cmpt-165-d100'
    
    def test_add_activity_components(self):
        
        c = CourseOffering.objects.get(slug = self.c_slug)
       
        #add an numeric activity and its components
        a = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0)
        a.save()
      
        co1 = ActivityComponent(numeric_activity = a, title = 'part1', max_mark = 20, position = 0)
        co2 = ActivityComponent(numeric_activity = a, title = 'part2', max_mark = 30, position = 1)
        co3 = ActivityComponent(numeric_activity = a, title = 'part3', max_mark = 50, position = 2)
        
        co1.save()
        co2.save()
        co3.save()
        
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)

        response = basic_page_tests(self, self.client, reverse(manage_activity_components, args=(self.c_slug,a.slug)))
          
        forms = response.context['formset'].forms
        self.assertEquals(forms[0].instance.title, 'part1')
        self.assertEquals(forms[1].instance.title, 'part2')
        self.assertEquals(forms[2].instance.title, 'part3') 
        
    def test_add_common_problems(self):
        c = CourseOffering.objects.get(slug =  self.c_slug)
        a = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0)
        a.save()        
        co1 = ActivityComponent(numeric_activity = a, title = 'part1', max_mark = 50, position = 0)
        co2 = ActivityComponent(numeric_activity = a, title = 'part2', max_mark = 50, position = 1) 
        co1.save()
        co2.save()
        
        #add some common problems
        cp1 = CommonProblem(activity_component = co1, title = 'cp1', penalty="0")
        cp2 = CommonProblem(activity_component = co1, title = 'cp2', penalty="1.12")        
        cp3 = CommonProblem(activity_component = co2, title = 'cp3', penalty="-2.3")
        
        cp1.save()
        cp2.save()
        cp3.save()
        
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)        

        response = basic_page_tests(self, self.client, reverse(manage_common_problems, args=(self.c_slug,a.slug)))
        
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
        url = reverse(marking_student, args=(self.c_slug,a.slug, '0aaa0'))
        response = basic_page_tests(self, self.client, url)
        
        mark_components = response.context['component_data']
        com1 = mark_components[0]
        com2 = mark_components[1]
        
        self.assertEquals(com1['component'], co1)
        self.assertEquals(len(com1['common_problems']), 2)
        self.assertEquals(com2['component'], co2)
        self.assertEquals(len(com2['common_problems']), 1)
       
    def test_post_activity_components(self):
        
        c = CourseOffering.objects.get(slug = self.c_slug)
       
        #add an numeric activity and its components
        a = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'RLS', \
                            due_date = datetime.now(), max_grade = 100, position = 0)
        a.save()
                                    
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)

        url = reverse(manage_activity_components, args=(self.c_slug, a.slug))

        # 2 forms for the first 2 components to add
        post_data = {'form-0-id' : ['', ''], 'form-1-id' : ['', ''],
                     'form-0-title': ['part1'], 'form-1-title': ['part2'], 
                     'form-0-max_mark' : ['20'], 'form-1-max_mark': ['20'],                    
                     'form-0-description' : ['basic1'], 'form-1-description': ['basic2'],
                     'form-TOTAL_FORMS' : ['3'], 'form-INITIAL_FORMS':['0']}
        
        response = self.client.post(url, post_data, follow = True)
        self.assertEquals(response.status_code, 200)
        
        cps = ActivityComponent.objects.filter(numeric_activity = a, deleted = False)
        self.assertEquals(len(cps), 2)
        self.assertEquals(cps[0].title, 'part1')        
        self.assertEquals(cps[1].title, 'part2')
        
        # keep the first 2 components, and add 2 more new components
        post_data2 = {'form-2-id' : ['', ''], 'form-3-id' : ['', ''],
                     'form-2-title': ['part3'], 'form-3-title': ['part4'], 
                     'form-2-max_mark' : ['30'], 'form-3-max_mark': ['30'],                    
                     'form-2-description' : ['advanced1'], 'form-3-description': ['advanced2'],
                     }
        post_data.update(post_data2)
       
        post_data['form-0-id'] = [str(cps[0].id), str(cps[0].id)]
        post_data['form-1-id'] = [str(cps[1].id), str(cps[1].id)]        
        post_data['form-INITIAL_FORMS'] = ['2']
        
        post_data['form-TOTAL_FORMS'] = ['5']
                
        response = self.client.post(url, post_data, follow = True)
        self.assertEquals(response.status_code, 200)
        cps = ActivityComponent.objects.filter(numeric_activity = a, deleted = False)
        self.assertEquals(len(cps), 4)
        self.assertEquals(cps[2].title, 'part3')        
        self.assertEquals(cps[3].title, 'part4')
    
    def test_group_setMark(self):
        c = CourseOffering.objects.get(slug = self.c_slug)
       
        #add an numeric activity
        a = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0)
        a.save()
        
        #take 2 students to make a group       
        stud1 = Member.objects.get(person = Person.objects.get(userid = '0aaa0'), offering = c)
        stud2 = Member.objects.get(person = Person.objects.get(userid = '0aaa1'), offering = c)
                
        group = Group.objects.create(courseoffering = c, name = 'hello', manager = stud1)
        member1 = GroupMember.objects.create(group = group, student = stud1, confirmed = True, activity=a)
        member2 = GroupMember.objects.create(group = group, student = stud2, confirmed = True, activity=a)
        
        group_mark = GroupActivityMark(group = group, numeric_activity = a)
        group_mark.setMark(30)
        group_mark.save()
        
        num_grades = NumericGrade.objects.filter(activity = a)
        self.assertEquals(len(num_grades), 2)
        self.assertEquals(num_grades[0].member, stud1)        
        self.assertEquals(num_grades[0].value, 30)     
        self.assertEquals(num_grades[0].flag, 'GRAD')
        self.assertEquals(num_grades[1].member, stud2) 
        self.assertEquals(num_grades[1].value, 30) 
        self.assertEquals(num_grades[1].flag, 'GRAD')
    
    def test_mark_history(self):
        c = CourseOffering.objects.get(slug = self.c_slug)
       
        #add an numeric activity
        a = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0)
        a.save()
        
        #take 2 students to make a group       
        stud1 = Member.objects.get(person = Person.objects.get(userid = '0aaa0'), offering = c)
        stud2 = Member.objects.get(person = Person.objects.get(userid = '0aaa1'), offering = c)
                
        group = Group.objects.create(courseoffering = c, name = 'hello', manager = stud1)
        member1 = GroupMember.objects.create(group = group, student = stud1, confirmed = True, activity=a)
        member2 = GroupMember.objects.create(group = group, student = stud2, confirmed = True, activity=a)
        
        ngrade = NumericGrade(activity = a, member = stud2)                  
        ngrade.save()
        
                 
        #assign mark to 0aaa1 individually twice and via the group twice, make some interval between saves     
        std_mark = StudentActivityMark(numeric_grade = ngrade, created_by = 'ggbaker')           
        std_mark.setMark(20)
        std_mark.save()  
               
        group_mark = GroupActivityMark(group = group, numeric_activity = a, created_by = 'ggbaker')  
        group_mark.setMark(30)
        group_mark.save()
        
        std_mark = StudentActivityMark(numeric_grade = ngrade, created_by = 'ggbaker')
        std_mark.setMark(40)
        std_mark.save()   
        
        group_mark = GroupActivityMark(group = group, numeric_activity = a,  created_by = 'ggbaker')
        group_mark.setMark(50)               
        group_mark.save()
        
        self.client.login(ticket = 'ggbaker', service=CAS_SERVER_URL)

        response = self.client.get(reverse('marking.views.mark_history_student', args=(self.c_slug, a.slug, '0aaa1')))
        self.assertEquals(response.status_code, 200)
        
        latest_act_mark = response.context['current_mark']
        self.assertEquals(len(response.context['marks_individual']), 2)
        self.assertEquals(len(response.context['marks_via_group']), 2)
        self.assertEquals(group_mark, latest_act_mark)

        
    def test_frontend(self):
        client = Client()
        client.login(ticket='ggbaker', service=CAS_SERVER_URL)
        
        # set up a course
        c = CourseOffering.objects.get(slug = self.c_slug)
        a1 = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0, group=True)
        a1.save()
        a2 = NumericActivity(offering = c, name = 'test_assignment_1', \
                            short_name = 'ta1', status = 'released', \
                            due_date = datetime.now(), max_grade = 100, position = 0, group=False)
        a2.save()
        
        stud1 = Member.objects.get(person = Person.objects.get(userid = '0aaa0'), offering = c)
        stud2 = Member.objects.get(person = Person.objects.get(userid = '0aaa1'), offering = c)
        instr = Member.objects.get(person = Person.objects.get(userid = 'ggbaker'), offering = c)
        group = Group.objects.create(courseoffering = c, name = 'hello', manager = stud1)
        member1 = GroupMember.objects.create(group = group, student = stud1, confirmed = True, activity=a1)
        member2 = GroupMember.objects.create(group = group, student = stud2, confirmed = True, activity=a1)
        
        # marking form (student)
        url = reverse('marking.views.marking_student', kwargs={'course_slug':c.slug, 'activity_slug':a2.slug, 'userid':stud1.person.userid})
        response = basic_page_tests(self, client, url)
        
        ac = ActivityComponent(numeric_activity=a2, max_mark=5, title="AC Title", description="AC Description", position=1, deleted=False)
        ac.save()
        ac = ActivityComponent(numeric_activity=a2, max_mark=5, title="AC Title2", description="AC Description2", position=2, deleted=False)
        ac.save()
        cp = CommonProblem(activity_component=ac, title="CP title", penalty=2, description="Cp description", deleted=False)
        cp.save()

        response = basic_page_tests(self, client, url)
        
        # submit the form and check that objects were created
        response = client.post(url, {'cmp-1-value': 5, 'cmp-1-comment': 'perfect', 'cmp-2-value': 3, 'cmp-2-comment': 'ok', 'mark_adjustment': 1, 'mark_adjustment_reason': 'reason', 'late_penalty': 10, u'overall_comment': 'overall'})
        self.assertEquals(response.status_code, 302)
        sam = StudentActivityMark.objects.filter(activity=a2, numeric_grade__member=stud1)
        self.assertEquals(len(sam), 1)
        sam = sam[0]
        self.assertEquals(sam.mark_adjustment, 1)
        self.assertEquals(sam.late_penalty, 10)
        self.assertEquals(sam.overall_comment, 'overall')
        self.assertEquals(sam.mark, decimal.Decimal("6.3"))
        acms = sam.activitycomponentmark_set.all()
        self.assertEquals(len(acms), 2)
        self.assertEquals(acms[0].value, 5)
        self.assertEquals(acms[0].comment, 'perfect')
        g = NumericGrade.objects.get(activity=a2, member=stud1)
        self.assertEquals(g.value, decimal.Decimal("6.3"))
        
        # make sure we get old data for "mark based on"
        response = basic_page_tests(self, client, url + "?base_activity_mark="+str(sam.id))
        self.assertContains(response, 'name="cmp-1-value" value="5"')
        self.assertContains(response, 'name="late_penalty" value="10"')

        # marking form (group)
        url = reverse('marking.views.marking_student', kwargs={'course_slug':c.slug, 'activity_slug':a1.slug, 'userid':stud1.person.userid})
        response = basic_page_tests(self, client, url)
        
        ac = ActivityComponent(numeric_activity=a1, max_mark=5, title="AC Title", description="AC Description", position=1, deleted=False)
        ac.save()
        ac = ActivityComponent(numeric_activity=a1, max_mark=5, title="AC Title2", description="AC Description2", position=2, deleted=False)
        ac.save()
        cp = CommonProblem(activity_component=ac, title="CP title", penalty=2, description="Cp description", deleted=False)
        cp.save()

        response = basic_page_tests(self, client, url)

        # common problem form
        url = reverse('marking.views.manage_common_problems', kwargs={'course_slug':c.slug, 'activity_slug':a2.slug})
        response = basic_page_tests(self, client, url)
        
        # mark all (student and group)
        url = reverse('marking.views.mark_all_students', kwargs={'course_slug':c.slug, 'activity_slug':a2.slug})
        response = basic_page_tests(self, client, url)
        # mark all (student and group)
        url = reverse('marking.views.mark_all_groups', kwargs={'course_slug':c.slug, 'activity_slug':a1.slug})
        response = basic_page_tests(self, client, url)

