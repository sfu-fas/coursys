from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from settings import CAS_SERVER_URL
from advisornotes.models import NonStudent, AdvisorNote
from courselib.testing import basic_page_tests
from dashboard.models import UserConfig


class AdvistorNotestest(TestCase):
    fixtures = ['test_data']

    def test_new_nonstudent_not_advisor(self):
        client = Client()
        client.login(ticket="0ppp0", service=CAS_SERVER_URL)
        response = client.get(reverse('advisornotes.views.new_nonstudent'))
        self.assertEqual(response.status_code, 403, "Student shouldn't have access")

    def test_new_nonstudent_is_advisor(self):
        client = Client()
        client.login(ticket="dzhao", service=CAS_SERVER_URL)
        response = client.get(reverse('advisornotes.views.new_nonstudent'))
        self.assertEqual(response.status_code, 200)

    def test_new_nonstudent_post_failure(self):
        client = Client()
        client.login(ticket="dzhao", service=CAS_SERVER_URL)
        response = client.post(reverse('advisornotes.views.new_nonstudent'), {'first_name': 'test123'})
        self.assertEqual(response.status_code, 200, "Should be brought back to form")
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 0, "Nonstudent should not have been created")

    def test_new_nonstudent_post_success(self):
        client = Client()
        client.login(ticket="dzhao", service=CAS_SERVER_URL)
        response = client.post(reverse('advisornotes.views.new_nonstudent'), {'first_name': 'test123', 'last_name': 'test_new_nonstudent_post'})
        self.assertEqual(response.status_code, 302, 'Should have been redirected')
        q = NonStudent.objects.filter(first_name='test123')
        self.assertEqual(len(q), 1, "There should only be one result")
        self.assertEqual(q[0].last_name, 'test_new_nonstudent_post')

    def test_artifact_notes_success(self):
        """
        Check overall pages for the grad module and make sure they all load
        """
        client = Client()
        client.login(ticket="dzhao", service=CAS_SERVER_URL)

        for view in ['new_nonstudent', 'new_artifact', 'view_artifacts',
                     'view_courses', 'view_course_offerings']:
            try:
                url = reverse('advisornotes.views.' + view, kwargs={})
                response = basic_page_tests(self, client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print "with view==" + repr(view)
                raise

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
        self.assertEqual(response.content, 'Necessary credentials not present')
        
    def test_rest_notes_not_advisor(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_not_advisor.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "User doesn't have the necessary permissions")
        
    def test_rest_notes_no_generated_token(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid.json')
        data = f.read()
        f.close()
        UserConfig.objects.get(user__userid='dzhao', key='advisor-token').delete()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "No token has been generated for user")
        
    def test_rest_notes_invalid_token(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_invalid_token.json')
        data = f.read()
        f.close()
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json; charset=utf-8')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content, "Secret token didn't match")
        
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
        
    def test_rest_notes_all_or_nothing(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_all_or_nothing.json')
        data = f.read()
        f.close()
        before_count = len(AdvisorNote.objects.all())
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 422)
        after_count = len(AdvisorNote.objects.all())
        self.assertEqual(before_count, after_count, "No advisor notes should be created if any are invalid")
        
    def test_rest_notes_success(self):
        client = Client()
        f = open('advisornotes/testfiles/rest_notes_valid.json')
        data = f.read()
        f.close()
        before_count = len(AdvisorNote.objects.filter(student__emplid=200000475))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        self.assertEqual(response.status_code, 200)
        after_count = len(AdvisorNote.objects.filter(student__emplid=200000475))
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
        before_count = len(AdvisorNote.objects.filter(student__emplid=200000475))
        response = client.post(reverse('advisornotes.views.rest_notes'), data, 'application/json')
        after_count = len(AdvisorNote.objects.filter(student__emplid=200000475))
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
