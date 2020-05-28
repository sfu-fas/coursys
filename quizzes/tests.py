import datetime

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from coredata.models import CourseOffering, Member
from courselib.testing import Client, TEST_COURSE_SLUG, test_views
from grades.models import Activity
from quizzes.forms import QuizImportForm
from quizzes.models import Quiz, Question, QuestionAnswer, TimeSpecialCase, QuestionVersion

now = datetime.datetime.now()
hour = datetime.timedelta(hours=1)


class QuizzesTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        # create some quiz data for testing
        self.offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        self.activity = Activity.objects.filter(offering=self.offering).first()

        self.quiz = Quiz(activity=self.activity, start=now - hour, end=now + 2*hour,
                         config={'intro': 'Quiz intro', 'markup': 'creole', 'math': False})
        self.quiz.save()

        self.q1 = Question(quiz=self.quiz, type='SHOR', order=1, config={'points': 10})
        self.q1.save()
        self.v11 = QuestionVersion(question=self.q1,
                                   config={'question': ('What do you think?', 'plain', False), 'max_length': 100})
        self.v11.save()
        self.v12 = QuestionVersion(question=self.q1,
                                   config={'question': ('What do you know?', 'plain', False), 'max_length': 100})
        self.v12.save()
        self.v13 = QuestionVersion(question=self.q1,
                                   config={'question': ('What do you wish?', 'plain', False), 'max_length': 100})
        self.v13.save()

        self.q2 = Question(quiz=self.quiz, type='MC', order=2, config={'points': 15})
        self.q2.save()
        self.v21 = QuestionVersion(question=self.q2, config={'question': ('Which **one**?', 'creole', False),
                                                             'options': [('one', 1), ('two', 0), ('three', 0)]})
        self.v21.save()

        self.q3 = Question(quiz=self.quiz, type='LONG', order=3, config={'points': 25})
        self.q3.save()
        self.v31 = QuestionVersion(question=self.q3, config={'question': ('Describe it.', 'creole', False),})
        self.v31.save()


        self.q4 = Question(quiz=self.quiz, type='FMT', order=4, config={'points': 25})
        self.q4.save()
        self.v41 = QuestionVersion(question=self.q4, config={'question': ('Write a lot, but fancier', 'creole', False),
                              'max_length': 10000, 'lines': 20})
        self.v41.save()

        self.q5 = Question(quiz=self.quiz, type='NUM', order=5, config={'points': 1})
        self.q5.save()
        self.v51 = QuestionVersion(question=self.q5, config={'question': ('Count', 'creole', False), 'resp_type': 'int'})
        self.v51.save()

        self.q6 = Question(quiz=self.quiz, type='NUM', order=5, config={'points': 1})
        self.q6.save()
        self.v61 = QuestionVersion(question=self.q6, config={'question': ('Measure', 'creole', False), 'resp_type': 'float'})
        self.v61.save()

        self.s0 = Member.objects.get(offering=self.offering, person__userid='0aaa0')
        self.s1 = Member.objects.get(offering=self.offering, person__userid='0aaa1')

        a01 = QuestionAnswer(question=self.q1, question_version=self.v11, student=self.s0, answer={'data': 'I like it.'})
        a01.save()
        a02 = QuestionAnswer(question=self.q2, question_version=self.v21, student=self.s0, answer={'data': 'B'})
        a02.save()
        a11 = QuestionAnswer(question=self.q1, question_version=self.v12, student=self.s1, answer={'data': 'I did not like it.'})
        a11.save()
        a12 = QuestionAnswer(question=self.q2, question_version=self.v21, student=self.s1, answer={'data': 'A'})
        a12.save()

        self.sc = TimeSpecialCase(quiz=self.quiz, student=self.s1, start=now - hour, end=now + 3*hour)
        self.sc.save()

        self.quiz.configure_marking()

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()
        c.login_user('ggbaker')

        # test as an instructor
        test_views(self, c, 'offering:quiz:',
                   ['index', 'preview_student', 'edit', 'question_add', 'submissions',
                    'special_cases', 'special_case_add', 'marking', 'strange_history', 'photo_compare'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug})

        test_views(self, c, 'offering:quiz:', ['question_add_version'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q1.id)})
        test_views(self, c, 'offering:quiz:', ['question_edit'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q1.id), 'version_id': str(self.v11.id)})
        test_views(self, c, 'offering:quiz:', ['question_edit'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q2.id), 'version_id': str(self.v21.id)})

        test_views(self, c, 'offering:quiz:', ['view_submission', 'submission_history'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'userid': self.s1.person.userid})
        test_views(self, c, 'offering:quiz:', ['mark_student'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'member_id': self.s1.id})

        # test as a student
        c.login_user(self.s0.person.userid)
        test_views(self, c, 'offering:quiz:', ['index'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug})

    def test_timing(self):
        """
        Ensure that the quiz timing rules are enforced for students
        """
        c = Client()
        c.login_user(self.s0.person.userid)
        url = reverse('offering:quiz:index', kwargs={'course_slug': self.offering.slug, 'activity_slug': self.activity.slug})

        # quiz created in .setUp() is ongoing
        response = c.get(url)
        self.assertTemplateUsed(response, 'quizzes/index_student.html')
        self.assertEqual(response.status_code, 200)

        # quiz in the future shouldn't be visible
        self.quiz.start = now + hour
        self.quiz.end = now + 2*hour
        self.quiz.save()

        response = c.get(url)
        self.assertTemplateUsed(response, 'quizzes/unavailable.html')
        self.assertEqual(response.status_code, 403)

        # neither should a quiz in the past
        self.quiz.start = now - 2*hour
        self.quiz.end = now - hour
        self.quiz.save()

        response = c.get(url)
        self.assertTemplateUsed(response, 'quizzes/unavailable.html')
        self.assertEqual(response.status_code, 403)

        # but the student with the special case has it honoured
        c.login_user(self.s1.person.userid)
        response = c.get(url)
        self.assertTemplateUsed(response, 'quizzes/index_student.html')
        self.assertEqual(response.status_code, 200)


class QuizImportTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        # create some quiz data for testing
        self.offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        self.activity = Activity.objects.filter(offering=self.offering).first()

        self.quiz = Quiz(activity=self.activity, start=now - hour, end=now + 2*hour,
                         config={'intro': 'Quiz intro', 'markup': 'creole', 'math': False})
        self.quiz.save()

    def run_import(self, json_data: str, bytes_data=None):
        if bytes_data is not None:
            file_dict = {'data': SimpleUploadedFile('test.json', bytes_data)}
        else:
            file_dict = {'data': SimpleUploadedFile('test.json', json_data.encode('utf-8'))}
        form = QuizImportForm(quiz=self.quiz, data={}, files=file_dict)
        if not form.is_valid():
            error_dict = form.errors
            msg = error_dict['data'][0]
            raise ValidationError(msg)

        return form.cleaned_data['data']

    def import_should_raise(self, json_data, message_re, bytes_data=None):
        with self.assertRaisesRegex(ValidationError, message_re):
            self.run_import(json_data, bytes_data=bytes_data)

    def test_bad_unicode(self):
        self.import_should_raise('', r'Bad UTF-8', bytes_data=b'\xf0\x28\x8c\x28')

    def test_bad_json(self):
        self.import_should_raise("{", r'Bad JSON')

    def test_empty(self):
        json_data = """{}"""
        self.import_should_raise(json_data, r'Missing "questions"')

    def test_config(self):
        json_data = """{ "config": 7, "questions": []}"""
        self.import_should_raise(json_data, r'must be a dict')

        json_data = """{ "config": {"unknown": "field", "secret": "notsecret"}, "questions": []}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertNotEqual(quiz.secret, 'notsecret')  # only some fields allowed past

        json_data = """{ "config": { "grace": 1234, "honour_code": false }, "questions": []}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(quiz.grace, 1234)
        self.assertEqual(quiz.honour_code, False)

    def test_intro(self):
        json_data = """{ "intro": ["foo", "creole"], "questions": [] }"""
        self.import_should_raise(json_data, r'must be a triple of')

        json_data = """{ "intro": ["foo", "unknown", true],  "questions": [] }"""
        self.import_should_raise(json_data, r'must be a triple of')

        json_data = """{ "intro": ["foo", 2, true],  "questions": [] }"""
        self.import_should_raise(json_data, r'must be a triple of')

        json_data = """{ "intro": ["foo", "unknown", 6],  "questions": [] }"""
        self.import_should_raise(json_data, r'must be a triple of')

        json_data = """{ "intro": ["foo", "creole", false],  "questions": [] }"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(quiz.intro, 'foo')
        self.assertEqual(quiz.markup, 'creole')
        self.assertEqual(quiz.math, False)

    def test_no_q(self):
        json_data = """{"questions": "many questions"}"""
        self.import_should_raise(json_data, r'must be a list')

        json_data = """{"questions": []}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(questions, [])
        self.assertEqual(versions, [])

    def test_question(self):
        json_data = """{"questions": [{ }]}"""
        self.import_should_raise(json_data, r'\["points"\] missing')

        json_data = """{"questions": [{ "points": "numbers" }]}"""
        self.import_should_raise(json_data, r'\["points"\] must be an integer')

        json_data = """{"questions": [{ "points": 1 }]}"""
        self.import_should_raise(json_data, r'\["type"\] missing')

        json_data = """{"questions": [{ "points": 1, "type": "unknown" }]}"""
        self.import_should_raise(json_data, r'\["type"\] must be a valid question type')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR" }]}"""
        self.import_should_raise(json_data, r'\["versions"\] missing')

    def test_version(self):
        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions": 7 }]}"""
        self.import_should_raise(json_data, r'\["versions"\] must be a list of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions": [] }]}"""
        self.import_should_raise(json_data, r'\["versions"\] must be a list of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions": [1,2,3] }]}"""
        self.import_should_raise(json_data, r'\["versions"\]\[0\] must be a dict')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions": [{}] }]}"""
        self.import_should_raise(json_data, r'\[0\] missing "text"')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": "foo" }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["text"\] must be a triple of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "creole"]}] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["text"\] must be a triple of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": [7, "creole", false] }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["text"\] must be a triple of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "unknown", false] }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["text"\] must be a triple of')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": 500 }] }]}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(len(questions), 1)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].config['text'], ('foo', 'markdown', False))

        json_data = """{"questions": [{ "points": 14, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": 123 },
            { "text": ["bar", "creole", true], "max_length": 234 }] }]}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(len(questions), 1)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].config['text'], ('foo', 'markdown', False))
        self.assertEqual(versions[1].config['text'], ('bar', 'creole', True))

    def test_question_type_validation(self):
        # ensure that the question types' form validation is doing it's thing
        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false] }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["max_length"\]: This field is required')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": "long" }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["max_length"\]: Enter a whole number')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": 30782398 }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["max_length"\]: Ensure this value is less than or equal')

        json_data = """{"questions": [{ "points": 1, "type": "SHOR", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": 917, "garbage": 9 }] }]}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEqual(versions[0].config['max_length'], 917)
        self.assertNotIn('garbage', versions[0].config)

        json_data = """{"questions": [{ "points": 1, "type": "CODE", "versions":
            [{ "text": ["foo", "markdown", false], "max_length": 917, "lines": 10, "language": "zazzy" }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["language"\]: Select a valid choice. zazzy is not one')

        # multiple choice has overrides: let's check that.
        json_data = """{"questions": [{ "points": 1, "type": "MC", "versions":
            [{ "text": ["foo", "markdown", false], "options": [] }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["options"\]: Must give at least two')

        json_data = """{"questions": [{ "points": 1, "type": "MC", "versions":
            [{ "text": ["foo", "markdown", false], "permute": "ouch", "options": [["good", 1], ["bad", 0]] }] }]}"""
        self.import_should_raise(json_data, r'\[0\]\["permute"\]: Select a valid choice. ouch is not')


        json_data = """{"questions": [{ "points": 1, "type": "MC", "versions":
            [{ "text": ["foo", "markdown", false], "permute": "permute", "options": [["good", 1], ["bad", 0]] }] }]}"""
        quiz, questions, versions = self.run_import(json_data)
        self.assertEquals(versions[0].config['options'], [('good', '1'), ('bad', '0')])
