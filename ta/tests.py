from django.test import TestCase
from courselib.testing import basic_page_tests, Client, test_views, TEST_COURSE_SLUG
from ta.models import CourseDescription, TAPosting, TAApplication, CampusPreference, CoursePreference, TUG
from coredata.models import Person, Semester, Unit, CourseOffering, Course, Role, Member
from ra.models import Account
from django.core.urlresolvers import reverse
from datetime import date

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
        d = CourseDescription(unit=unit, description="Lab TA", labtut=True)
        d.save()
        d = CourseDescription(unit=unit, description="Office Hours", labtut=False)
        d.save()

        #Create posting that closes in a long time so no applications are late
        posting = TAPosting(semester=s, unit=unit,opens=date(2007,9,4), closes=date(2099,9,4))
        posting.config['accounts'] = [a.id for a in Account.objects.all()]
        posting.config['start'] = date(2100,10,10)
        posting.config['end'] = date(2101,10,10)
        posting.config['deadline'] = date(2099,9,20)
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
        client.login_user(userid)     

        #Check that assign_tas page has two courses in it, one with someone who has applied
        url = reverse('ta.views.assign_tas', kwargs={'post_slug': posting.slug,})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<a href="/ta/%s/%s"' % (posting.slug, self.co1.slug) )
        self.assertContains(response, '<a href="/ta/%s/%s"' % (posting.slug, self.co2.slug) )
        self.assertContains(response, '<td class="num">1</td>')

        #Check the view application page to make sure it displays properly
        url = reverse('ta.views.view_application', kwargs={'post_slug': posting.slug, 'userid':app.person.userid,})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<a href="mailto:%s@sfu.ca"' % (app.person.userid) )
        self.assertContains(response, '<td>%s</td>' % (c1) )
       
        #Check the assign_bu page to make sure applicant appears
        url = reverse('ta.views.assign_bus', kwargs={'post_slug': posting.slug, 'course_slug':self.co1.slug,})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<a href="/ta/%s/application/%s"' % (posting.slug, app.person.userid) )
       
        #Assign bu's to the applicant and make sure they show up on assign_ta page 
        post_data = {
            'form-TOTAL_FORMS':2,
            'form-INITIAL_FORMS':1,
            'form-MAX_NUM_FORMS':'',
            'form-0-rank':1,
            'form-0-bu':2.0,
        }
        response = client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<td class="num">2.00</td>')



    def test_pages(self):
        c = Client()

        # TUG/instructor views
        c.login_user('ggbaker')
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        ta = Member.objects.filter(offering=offering, role="TA")[0]
        test_views(self, c, 'ta.views.', ['new_tug'], {'course_slug': offering.slug, 'userid': ta.person.userid})

        # create TUG to view/edit
        tug = TUG(member=ta, base_units=5)
        for f in tug.config_meta.keys():
            tug.config[f] = {'weekly': 1, 'total': 13, 'note': 'somenote'}
        tug.save()
        test_views(self, c, 'ta.views.', ['view_tug', 'edit_tug'], {'course_slug': offering.slug, 'userid': ta.person.userid})

        # admin views
        c.login_user('ggbaker')
        test_views(self, c, 'ta.views.', ['all_tugs_admin', 'view_postings'], {})
        post = TAPosting.objects.filter(unit__label='CMPT')[0]
        test_views(self, c, 'ta.views.', ['new_application', 'new_application_manual', 'view_all_applications',
                    'print_all_applications', 'print_all_applications_by_course', 'view_late_applications',
                    'assign_tas', 'all_contracts'],
                {'post_slug': post.slug})
        test_views(self, c, 'ta.views.', ['assign_bus'],
                {'post_slug': post.slug, 'course_slug': offering.slug})

        app = TAApplication.objects.filter(posting=post)[0]
        test_views(self, c, 'ta.views.', ['edit_application', 'view_application', 'preview_offer', 'view_contract',
                                          'edit_contract'],
                   {'post_slug': post.slug, 'userid': app.person.userid})

        # applicant views
        c.login_user(app.person.userid)
        test_views(self, c, 'ta.views.', ['accept_contract'],
                   {'post_slug': post.slug, 'userid': app.person.userid})






