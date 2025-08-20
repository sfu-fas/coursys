import datetime

from django.test import TestCase

from django.urls import reverse
from coredata.models import Person, Unit
from advisornotes.models import NonStudent, AdvisorNote, AdvisorVisit, AdvisorVisitSurvey
from courselib.testing import basic_page_tests, Client, freshen_roles


class AdvisorNotestest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_pages(self):
        freshen_roles()
        client = Client()
        client.login_user("dzhao")
        adv = Person.objects.get(userid='dzhao')

        # create some notes to work with
        unit = Unit.objects.get(slug='cmpt')
        ns = NonStudent(first_name="Non", last_name="Student", high_school="North South Burnaby-Surrey",
                        start_year=2000)
        ns.save()
        p1 = Person.objects.get(userid='0aaa6')
        n1 = AdvisorNote(student=p1, text="He seems like a nice student.", unit=unit, advisor=adv)
        n1.save()
        p2 = Person.objects.get(userid='0aaa8')
        p2.userid = None
        p2.save()
        n2 = AdvisorNote(student=p2, text="This guy doesn't have an active computing account.", unit=unit, advisor=adv)
        n2.save()
        n3 = AdvisorNote(nonstudent=ns, text="What a horrible person.", unit=unit, advisor=adv)
        n3.save()

        # index page
        url = reverse('advising:advising', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # list nonstudents
        url = reverse('advising:view_nonstudents', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # new nonstudent form
        url = reverse('advising:new_nonstudent', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # student with userid
        url = reverse('advising:advising', kwargs={})
        response = client.post(url, {'search': p1.emplid})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advising:student_notes', kwargs={'userid': p1.userid})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advising:new_note', kwargs={'userid': p1.userid})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # student with no userid
        response = client.post(url, {'search': p2.emplid})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advising:student_notes', kwargs={'userid': p2.emplid})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advising:new_note', kwargs={'userid': p2.emplid})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # non student
        response = client.post(url, {'search': ns.slug})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advising:student_notes', kwargs={'userid': ns.slug})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advising:new_note', kwargs={'userid': ns.slug})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # note content search
        url = reverse('advising:note_search', kwargs={}) + "?text-search=nice"
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notes']), 1)
        url = reverse('advising:note_search', kwargs={}) + "?text-search="
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notes']), 3)

        # news page
        url = reverse('advising:news', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # new announcement page
        url = reverse('advising:new_announcement', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # my surveys
        url = reverse('advising:view_my_surveys', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

    def test_new_nonstudent_not_advisor(self):
        client = Client()
        client.login_user("0ppp0")
        response = client.get(reverse('advising:new_nonstudent'))
        self.assertEqual(response.status_code, 403, "Student shouldn't have access")

    def test_new_nonstudent_is_advisor(self):
        freshen_roles()
        client = Client()
        client.login_user("dzhao")
        response = client.get(reverse('advising:new_nonstudent'))
        self.assertEqual(response.status_code, 200)

    def test_new_nonstudent_post_failure(self):
        freshen_roles()
        client = Client()
        client.login_user("dzhao")
        response = client.post(reverse('advising:new_nonstudent'), {'first_name': 'test123'})
        self.assertEqual(response.status_code, 200, "Should be brought back to form")
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 0, "Nonstudent should not have been created")

    def test_new_nonstudent_post_success(self):
        freshen_roles()
        client = Client()
        client.login_user("dzhao")
        year = datetime.date.today().year
        now = datetime.datetime.now()
        response = client.post(reverse('advising:new_nonstudent'), {'first_name': 'test123', 'last_name': 'test_new_nonstudent_post', 'start_year': year, 
                                                                    'email_address': 'alan.turing@example.net', 'created_at': now})
        self.assertEqual(response.status_code, 302, 'Should have been redirected')
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 1, "There should only be one result")
        self.assertEqual(q[0].last_name, 'test_new_nonstudent_post')

    def test_artifact_notes_success(self):
        """
        Check overall pages for the grad module and make sure they all load
        """
        freshen_roles()
        client = Client()
        client.login_user("dzhao")

        for view in ['new_nonstudent', 'view_nonstudents', 'new_artifact', 'view_artifacts',
                     'view_courses', 'view_course_offerings', 'view_all_semesters']:
            try:
                url = reverse('advising:' + view, kwargs={})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print("with view==" + repr(view))
                raise

    def test_surveys(self):
        freshen_roles()
        client = Client()
        client.login_user("dzhao")

        # create visit
        p1 = Person.objects.get(userid='0aaa1')
        unit = Unit.objects.get(slug='cmpt')
        adv = Person.objects.get(userid='dzhao')
        visit = AdvisorVisit(student=p1, nonstudent=None, unit=unit, advisor=adv, version=1)
        visit.save()

        # advisor can view visit
        url = reverse('advising:view_visit', kwargs={'visit_slug': visit.slug})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        survey = AdvisorVisitSurvey(visit=visit, created_by=adv)
        survey.save()

        # advisor can view survey results
        url = reverse('advising:view_survey', kwargs={'key': survey.key})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
