from django.test import TestCase

from django.core.urlresolvers import reverse
from coredata.models import Person, Unit
from advisornotes.models import NonStudent, AdvisorNote
from courselib.testing import basic_page_tests, Client

class AdvisorNotestest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_pages(self):
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
        url = reverse('advisornotes.views.advising', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # new nonstudent form
        url = reverse('advisornotes.views.new_nonstudent', kwargs={})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # student with userid
        url = reverse('advisornotes.views.advising', kwargs={})
        response = client.post(url, {'search': p1.emplid})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advisornotes.views.student_notes', kwargs={'userid': p1.userid})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advisornotes.views.new_note', kwargs={'userid': p1.userid})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # student with no userid
        response = client.post(url, {'search': p2.emplid})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advisornotes.views.student_notes', kwargs={'userid': p2.emplid})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advisornotes.views.new_note', kwargs={'userid': p2.emplid})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # non student
        response = client.post(url, {'search': ns.slug})
        self.assertEqual(response.status_code, 302)
        redir_url = response['location']
        student_url = reverse('advisornotes.views.student_notes', kwargs={'userid': ns.slug})
        self.assertIn(student_url, redir_url)
        response = basic_page_tests(self, client, student_url, check_valid=False)
        self.assertEqual(response.status_code, 200)
        new_url = reverse('advisornotes.views.new_note', kwargs={'userid': ns.slug})
        response = basic_page_tests(self, client, new_url)
        self.assertEqual(response.status_code, 200)

        # note content search
        url = reverse('advisornotes.views.note_search', kwargs={}) + "?text-search=nice"
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notes']), 1)
        url = reverse('advisornotes.views.note_search', kwargs={}) + "?text-search="
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notes']), 3)

    def test_new_nonstudent_not_advisor(self):
        client = Client()
        client.login_user("0ppp0")
        response = client.get(reverse('advisornotes.views.new_nonstudent'))
        self.assertEqual(response.status_code, 403, "Student shouldn't have access")

    def test_new_nonstudent_is_advisor(self):
        client = Client()
        client.login_user("dzhao")
        response = client.get(reverse('advisornotes.views.new_nonstudent'))
        self.assertEqual(response.status_code, 200)

    def test_new_nonstudent_post_failure(self):
        client = Client()
        client.login_user("dzhao")
        response = client.post(reverse('advisornotes.views.new_nonstudent'), {'first_name': 'test123'})
        self.assertEqual(response.status_code, 200, "Should be brought back to form")
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 0, "Nonstudent should not have been created")

    def test_new_nonstudent_post_success(self):
        client = Client()
        client.login_user("dzhao")
        response = client.post(reverse('advisornotes.views.new_nonstudent'), {'first_name': 'test123', 'last_name': 'test_new_nonstudent_post', 'start_year': 2020})
        self.assertEqual(response.status_code, 302, 'Should have been redirected')
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 1, "There should only be one result")
        self.assertEqual(q[0].last_name, 'test_new_nonstudent_post')

    def test_artifact_notes_success(self):
        """
        Check overall pages for the grad module and make sure they all load
        """
        client = Client()
        client.login_user("dzhao")

        for view in ['new_nonstudent', 'new_artifact', 'view_artifacts',
                     'view_courses', 'view_course_offerings', 'view_all_semesters']:
            try:
                url = reverse('advisornotes.views.' + view, kwargs={})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise

"""
class AdvisorNotesAPITest(TestCase):
#class AdvistorNotesAPITest(object):
    fixtures = ['test_data']

    def test_rest_notes_not_POST(self):
        client = Client()
        response = client.get(reverse('advisornotes.views.rest_notes'))
        self.assertEqual(response.status_code, 405, "Should get a 405 for non POST requests")

    def test_rest_notes_invalid_JSON(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_bad_json.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Bad JSON in request body')

    def test_rest_notes_invalid_UTF8(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_bad_utf8.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Bad UTF-8 encoded text')

    def test_rest_notes_not_JSON(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid_file.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'text/plain')
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.content, 'Contents must be JSON (application/json)')

    def test_rest_notes_missing_credential(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_missing_credential.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "The key 'secret' is not present. ")

    def test_rest_notes_not_advisor(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_not_advisor.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        from coredata.validate_rest import _token_not_found
        self.assertEqual(response.content, _token_not_found)

    def test_rest_notes_no_generated_token(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid.json')
        data = f.read()
        f.close()
        UserConfig.objects.get(user__userid='dzhao', key='advisor-token').delete()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        from coredata.validate_rest import _token_not_found
        self.assertEqual(response.content, _token_not_found)

    def test_rest_notes_invalid_token(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_invalid_token.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json; charset=utf-8')
        self.assertEqual(response.status_code, 422)
        from coredata.validate_rest import _token_not_found
        self.assertEqual(response.content, _token_not_found)

    def test_rest_notes_no_notes(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_no_notes.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "No advising notes present")

    def test_rest_notes_not_list(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_not_list.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Notes not in list format")

    def test_rest_notes_empty_list(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_empty.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "No advising notes present")

    def test_rest_notes_emplid_text_missing(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_emplid_missing.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Emplid or text not present in note")

    def test_rest_notes_emplid_not_int(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_emplid_not_int.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Note emplid must be an integer")

    def test_rest_notes_text_not_text(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_text_not_text.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Note text must be a string")

    def test_rest_notes_emplid_doesnt_exist(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_emplid_doesnt_exist.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Emplid '321' doesn't exist")


    def test_rest_notes_success(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid.json')
        data = f.read()
        f.close()
        before_count = len(AdvisorNote.objects.filter(student__emplid=200000341))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 200)
        after_count = len(AdvisorNote.objects.filter(student__emplid=200000341))
        self.assertEqual(before_count + 2, after_count, "There should be two more notes for the student")

    def test_rest_notes_filename_not_string(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_filename_not_string.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Note filename must be a string")

    def test_rest_notes_mediatype_not_string(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_mediatype_not_string.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Note mediatype must be a string")

    def test_rest_notes_file_data_not_string(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_file_data_not_string.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Note file data must be a string")

    def test_rest_notes_file_success(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid_file.json')
        data = f.read()
        f.close()
        before_count = len(AdvisorNote.objects.filter(student__emplid=200000341))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        after_count = len(AdvisorNote.objects.filter(student__emplid=200000341))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before_count + 1, after_count, "Should be one more advisor note for student")

    def test_rest_notes_bad_base64(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_bad_base64.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Invalid base64 data for note file attachment")

    def DISABLED_test_rest_notes_no_problems(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_no_problems.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "No problems present")

    def DISABLED_test_rest_notes_problems_not_list(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problems_not_list.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Problems not in list format")

    def DISABLED_test_rest_notes_problems_empty(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problems_empty.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "No problems present")

    def DISABLED_test_rest_notes_problem_fields_missing(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_fields_missing.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Necessary fields not present in problem")

    def DISABLED_test_rest_notes_problem_emplid_not_int(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_emplid_not_int.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Problem emplid & resolution_lasts must be integers")

    def DISABLED_test_rest_notes_problem_emplid_invalid(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_emplid_invalid.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Emplid '123' doesn't exist")

    def DISABLED_test_rest_notes_problem_resolution_zero(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_resolution_zero.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Resolution_lasts must be greater than zero")

    def DISABLED_test_rest_notes_problem_code_not_string(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_code_not_string.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Problem code & description must be strings")

    def DISABLED_test_rest_notes_problem_description_too_long(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_description_too_long.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Problem code & description must be less than or equal to 30 & 50 characters respectively")

    def DISABLED_test_rest_notes_problem_unit_invalid(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_unit_invalid.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Unit 'NOTREAL' does not exist")

    def DISABLED_test_rest_notes_problem_comments_not_string(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_comments_not_string.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Problem comments must be a string")

    def DISABLED_test_rest_notes_problem_already_exists(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problem_already_exists.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        before_count = len(Problem.objects.filter(person__emplid=200000172))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        after_count = len(Problem.objects.filter(person__emplid=200000172))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before_count, after_count, "Shouldn't duplicate problem")

    def DISABLED_test_rest_notes_problems_successful(self):
        raise SkipTest()
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_problems_successful.json')
        data = f.read()
        f.close()
        
        # check that a duplicate isn't saved
        p = Problem(person=Person.objects.get(emplid=200000172), code='Deceased', status='RESO',
                    resolved_at=datetime.datetime.now(), resolution_lasts=10,
                    resolved_until=datetime.datetime.now()+datetime.timedelta(days=10),
                    unit=Unit.objects.get(slug='cmpt'))
        p.save()
        
        before_count = len(Problem.objects.filter(person__emplid=200000172))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        after_count = len(Problem.objects.filter(person__emplid=200000172))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before_count + 1, after_count, "Only one problem should have been created")

"""