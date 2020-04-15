# TODO: a QuestionMark model and the UI for TAs to enter marks
# TODO: delete Quiz?

import datetime
import json
from collections import namedtuple
from importlib import import_module
from typing import Optional, Tuple, List

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore
from django.core.checks import Error
from django.db import models
from django.db.models import Max
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.utils.safestring import SafeText
from ipware import get_client_ip

from coredata.models import Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from grades.models import Activity
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.types.mc import MultipleChoice
from quizzes.types.text import ShortAnswer, LongAnswer, FormattedAnswer, NumericAnswer


QUESTION_TYPE_CHOICES = [
    ('MC', 'Multiple Choice, single answer'),
    #('MCM', 'Multiple Choice, multiple answer'),
    ('SHOR', 'Short Answer (one line)'),
    ('LONG', 'Long Answer (several lines)'),
    ('FMT', 'Long Answer with formatting'),
    ('NUM', 'Numeric Answer'),
    #('FILE', 'File Upload'),
    #('INST', 'Instructions (students enters nothing)'),
]


QUESTION_CLASSES = {
    'MC': MultipleChoice,
    'SHOR': ShortAnswer,
    'LONG': LongAnswer,
    'FMT': FormattedAnswer,
    'NUM': NumericAnswer,
}


STATUS_CHOICES = [
    ('V', 'Visible'),
    ('D', 'Deleted'),
]


class Quiz(models.Model):
    class QuizStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('activity', 'activity__offering').filter(status='V')

    activity = models.OneToOneField(Activity, on_delete=models.PROTECT)
    start = models.DateTimeField(help_text='Quiz will be visible to students after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(help_text='Quiz will be invisible to students and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # q.config['intro']: introductory text for the quiz
        # q.config['markup']: markup language used: see courselib/markup.py
        # q.config['math']: intro uses MathJax? (boolean)

    intro = config_property('intro', default='')
    markup = config_property('markup', default='')
    math = config_property('math', default='')

    class Meta:
        verbose_name_plural = 'Quizzes'

    objects = QuizStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.activity.offering.slug, activity_slug=self.activity.slug)

    def get_start_end(self, member: Optional[Member]) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Get the start and end times for this quiz.

        The start/end may have been overridden by the instructor for this student, but default to .start and .end if not
        """
        if not member:
            # in the generic case, use the defaults
            return self.start, self.end

        special_case = TimeSpecialCase.objects.filter(quiz=self, student=member).first()
        if not special_case:
            # no special case for this student
            return self.start, self.end
        else:
            # student has a special case
            return special_case.start, special_case.end

    def ongoing(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz currently in-progress?
        """
        start, end = self.get_start_end(member=member)
        if not start or not end:
            # newly created with start and end not yet filled
            return False
        now = datetime.datetime.now()
        return start <= now <= end

    def completed(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz over?
        """
        _, end = self.get_start_end(member=member)
        if not end:
            # newly created with end not yet filled
            return False
        now = datetime.datetime.now()
        return now > end

    def intro_html(self) -> SafeText:
        return markup_to_html(self.intro, markuplang=self.markup, math=self.math)


class Question(models.Model):
    class QuestionStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(status='V')

    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    type = models.CharField(max_length=4, null=False, blank=False, choices=QUESTION_TYPE_CHOICES)
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    order = models.PositiveSmallIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # q.config['points']: points the question is worth (positive integer)
        # q.config['question']: question as (text, markup, math:bool)
        # others as set by the .type (and corresponding QuestionType)

    points = config_property('points', default=0)
    question = config_property('question', default=('', DEFAULT_QUIZ_MARKUP, False))

    class Meta:
        ordering = ['order']

    objects = QuestionStatusManager()
    all_objects = models.Manager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.quiz.activity.offering.slug,
                           activity_slug=self.quiz.activity.slug) + '#' + self.ident()

    def ident(self):
        """
        Unique identifier that can be used as a input name or HTML id value.
        """
        return 'q-%i' % (self.id,)

    def set_order(self):
        """
        If the question has no .order, set the .order value to the current max + 1
        """
        if self.order is not None:
            return

        current_max = Question.objects.filter(quiz=self.quiz).aggregate(Max('order'))['order__max']
        if not current_max:
            self.order = 1
        else:
            self.order = current_max + 1

    def helper(self):
        return QUESTION_CLASSES[self.type](question=self)

    def question_html(self):
        text, markup, math = self.question
        return markup_to_html(text, markup, math=math)

    def entry_field(self, questionanswer: 'QuestionAnswer' = None):
        helper = self.helper()
        return helper.get_entry_field(questionanswer=questionanswer)


class QuestionAnswer(models.Model):
    class AnswerStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('question').filter(question__status='V')

    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    answer = JSONField(null=False, blank=False, default=dict)
    # format of .answer determined by the corresponding QuestionHelper

    class Meta:
        unique_together = [['question', 'student']]

    objects = AnswerStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:view_submission', course_slug=self.question.quiz.activity.offering.slug,
                           activity_slug=self.question.quiz.activity.slug,
                           userid=self.student.person.userid_or_emplid()) + '#' + self.question.ident()

    def answer_html(self) -> SafeText:
        helper = self.question.helper()
        return helper.to_html(self)


class QuizSubmission(models.Model):
    """
    Model to log everything we can think of about a quiz submission, for possibly later analysis.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, null=False, blank=False, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    ip_address = models.GenericIPAddressField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)  # additional data about the submission:
    # .config['answers']: list of QuestionAnswer objects submitted (if changed from prev submission), as [(Question.id, answer)]
    # .config['user_agent']: HTTP User-Agent header from submission
    # .config['session']: the session_key from the submission
    # .config['csrf_token']: the CSRF token being used for the submission
    # .config['fingerprint']: browser fingerprint provided by fingerprintjs2

    @classmethod
    def create(cls, request: HttpRequest, quiz: Quiz, student: Member, answers: List[QuestionAnswer], commit: bool = True) -> 'QuizSubmission':
        qs = cls(quiz=quiz, student=student)
        ip_addr, _ = get_client_ip(request)
        qs.ip_address = ip_addr
        qs.config['answers'] = [(a.question_id, a.answer) for a in answers]
        qs.config['session'] = request.session.session_key
        qs.config['csrf_token'] = request.META.get('CSRF_COOKIE')
        qs.config['user_agent'] = request.META.get('HTTP_USER_AGENT')
        try:
            qs.config['fingerprint'] = json.loads(request.POST['fingerprint'])
        except KeyError:
            qs.config['fingerprint'] = 'missing'
        except json.JSONDecodeError:
            qs.config['fingerprint'] = 'json-error'

        if commit:
            qs.save()
        return qs

    @classmethod
    def check(cls, **kwargs):
        """
        We use .session_key and CSRF_COOKIE above: check that they will be there, and fail fast if not.
        """
        errors = super().check(**kwargs)

        # Ensure we are using the database session store. (Other SessionStores may also have .session_key?)
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore
        if not issubclass(store, DatabaseSessionStore):
            errors.append(Error(
                "Quiz logging uses request.session.session_key, which likely implies "
                "SESSION_ENGINE = 'django.contrib.sessions.backends.db' in settings."
            ))

        if 'django.middleware.csrf.CsrfViewMiddleware' not in settings.MIDDLEWARE:
            errors.append(Error(
                "CsrfViewMiddleware is not enabled in settings: quiz logging uses CSRF_COOKIE and will fail without "
                "CSRF checking enabled. Also it should be enabled in general."
            ))

        return errors

    AnswerData = namedtuple('AnswerData', ['question', 'n', 'answer', 'answer_html'])

    def annotate_questions(self, questions: List[Question]) -> None:
        """
        Annotate this object to combine .config['answers'] and questions for efficient display later.
        """
        answers = self.config['answers']
        question_lookup = {q.id: (q, i+1) for i,q in enumerate(questions)}
        answer_data = []
        for question_id, answer in answers:
            question, n = question_lookup[question_id]
            # temporarily reconstruct the QuestionAnswer so we can generate HTML
            qa = QuestionAnswer(question=question, student=self.student, modified_at=self.created_at, answer=answer)
            answer_html = question.helper().to_html(qa)
            data = QuizSubmission.AnswerData(question=question, n=n, answer=answer, answer_html=answer_html)
            answer_data.append(data)

        self.answer_data = answer_data

    def session_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's session on submission.
        We could incorporate csrf_token here, but are we *sure* it only changes on login?
        """
        ident = self.config['session'] # + '--' + self.config['csrf_token']
        return '%08x' % (hash(ident) % (16**8),)

    def browser_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's browser on submission.
        """
        # including user_agent is generally redundant, but not if the fingerprinting fails for some reason
        ident = self.config['user_agent'] + '--' + json.dumps(self.config['fingerprint'])
        return '%08x' % (hash(ident) % (16**8),)


class TimeSpecialCase(models.Model):
    """
    Model to represent quiz start/end times that are unique to one student, to allow makeup quizzes, accessibility
    accommodations, etc.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    start = models.DateTimeField(help_text='Quiz will be visible to the student after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(help_text='Quiz will be invisible to the student and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        unique_together = [['quiz', 'student']]

#class QuestionMark(models.Model):



