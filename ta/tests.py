from django.test import TestCase
from ta.models import *
from coredata.models import Role
from settings import CAS_SERVER_URL

from django.test.client import Client
from django.core.urlresolvers import reverse

from datetime import date, datetime

class ApplicationTest(TestCase):
    fixtures = ['test_data']
    def setUp(self):
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p1.save()
        
        s = Semester(name="1077", start=date(2007,9,4), end=date(2007,12,3))
        s.save()
    
        unit = Unit.objects.get(label="CMPT")
        self.co1 = CourseOffering(owner=unit, subject="CMPT", number="120", section="D100", semester=s, component="LEC",
                            graded=True, crse_id=11111, class_nbr=22222, campus='BRNBY', title="Computer Stuff",
                            enrl_cap=100, enrl_tot=99, wait_tot=2)
        
        self.co2 = CourseOffering(owner=unit, subject="CMPT", number="165", section="D100", semester=s, component="LEC",
                            graded=True, crse_id=22222, class_nbr=11111, campus='SURRY', title="Web Stuff",
                            enrl_cap=85, enrl_tot=80, wait_tot=4)
        self.co1.save()
        self.co2.save()

    def test_application(self):
        p = Person.objects.get(emplid=210012345)
        s = Semester.objects.get(name="1077")
        unit = Unit.objects.get(label="CMPT")

        #Create posting that closes in a long time so no applications are late
        posting = TAPosting(semester=s, unit=unit,opens=date(2007,9,4), closes=date(2099,9,4))
        posting.save() 

        #Create application for posting as well as campus and course preferences
        app = TAApplication(posting=posting, person=p, category="UTA", base_units=2, sin="123123123", course_load="No Other Courses")
        app.save()

        cp1 = CampusPreference(app=app, campus="BRNBY", pref="PRF")
        cp2 = CampusPreference(app=app, campus="SURRY", pref="NOT")
        cp1.save()
        cp2.save()

        c1 = Course.objects.get(subject="CMPT", number="120")
        
        course1 = CoursePreference(app=app, course=c1, taken="YES", exper="FAM", rank=1)
        course1.save()

        #Login a ta admin
        client = Client()
        userid = Role.objects.filter(role="TAAD")[0].person.userid
        client.login(ticket=userid, service=CAS_SERVER_URL)     

        #Check that assign_tas page has two courses in it, one with someone who has applied
        url = reverse('ta.views.assign_tas', kwargs={'post_slug': posting.slug,})
        response = client.get(url) 
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<a href="/ta/%s/%s"' % (posting.slug, self.co1.slug) )
        self.assertContains(response, '<a href="/ta/%s/%s"' % (posting.slug, self.co2.slug) )
        self.assertContains(response, '<td class="num">1</td>')

        #Check the view application page to make sure it displays properly
        url = reverse('ta.views.view_application', kwargs={'post_slug': posting.slug, 'userid':app.person.userid,})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<a href="mailto:%s@sfu.ca"' % (app.person.userid) )
        self.assertContains(response, '<td>%s</td>' % (c1) )
