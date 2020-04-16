import datetime

from django.test import TestCase
from django.urls import reverse

from coredata.models import CourseOffering, Member
from courselib.testing import Client, TEST_COURSE_SLUG, test_views
from grades.models import Activity
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
                                                             'options': ['one', 'two', 'three']})
        self.v21.save()

        self.q3 = Question(quiz=self.quiz, type='LONG', order=3, config={'points': 25})
        self.q3.save()
        self.v31 = QuestionVersion(question=self.q3, config={'question': ('Which **one**?', 'creole', False),
                                                             'options': ['one', 'two', 'three']})
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

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()
        c.login_user('ggbaker')

        # test as an instructor
        test_views(self, c, 'offering:quiz:',
                   ['index', 'preview_student', 'edit', 'question_add', 'submissions',
                    'special_cases', 'special_case_add'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug})

        test_views(self, c, 'offering:quiz:', ['question_add_version'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q1.id)})
        test_views(self, c, 'offering:quiz:', ['question_edit'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q1.id), 'version_id': str(self.v11.id)})
        test_views(self, c, 'offering:quiz:', ['question_edit'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'question_id': str(self.q2.id), 'version_id': str(self.v21.id)})

        test_views(self, c, 'offering:quiz:', ['view_submission', 'submission_history'],
                   {'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'userid': self.s1.person.userid})

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
