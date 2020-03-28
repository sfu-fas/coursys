# TODO: override start/end times for special-case students (somehow)
# TODO: a QuestionMark model and the UI for TAs to enter marks

import datetime

from django.db import models
from django.db.models import Max
from django.shortcuts import resolve_url
from django.utils.safestring import SafeText, mark_safe

from coredata.models import Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from grades.models import Activity
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.types.text import ShortAnswer


QUESTION_TYPE_CHOICES = [
    ('MC', 'Multiple Choice, single answer'),
    ('MCM', 'Multiple Choice, multiple answer'),
    ('SHOR', 'Short Answer (one line)'),
    ('MEDI', 'Medium Answer (a few line)'),
    ('LONG', 'Long Answer (longer)'),
    ('NUM', 'Numeric Answer'),
    ('FILE', 'File Upload'),
    ('INST', 'Instructions (students enter nothing)'),
]


QUESTION_CLASSES = {
    'SHOR': ShortAnswer,
}


STATUS_CHOICES = [
    ('V', 'Visible'),
    ('D', 'Deleted'),
]


class VisibleStatusManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='V')


class Quiz(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.PROTECT)
    start = models.DateTimeField(help_text='Quiz will be visible to student after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(help_text='Quiz will be invisible to students and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # q.config['intro']: introductory text for the quiz
        # q.config['markup']: markup language used: see courselib/markup.py
        # q.config['math']: page uses MathJax? (boolean)

    intro = config_property('intro', default='')
    markup = config_property('markup', default='')
    math = config_property('math', default='')

    class Meta:
        verbose_name_plural = 'Quizzes'

    objects = VisibleStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.activity.offering.slug, activity_slug=self.activity.slug)

    def intro_html(self) -> SafeText:
        return markup_to_html(self.intro, markuplang=self.markup, math=self.math)


class Question(models.Model):
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
        unique_together = [['quiz', 'order']]

    objects = VisibleStatusManager()

    def set_order(self):
        """
        Set the .order value to the current max + 1
        """
        current_max = Question.objects.filter(quiz=self.quiz).aggregate(Max('order'))['order__max']
        if not current_max:
            self.order = 1
        else:
            self.order = current_max + 1

    def question_html(self):
        text, markup, math = self.question
        return markup_to_html(text, markup, math=math)



class QuestionAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    answer = JSONField(null=False, blank=False, default=dict)
    # format of .answer determined by the corresponding QuestionType

    class Meta:
        unique_together = [['question', 'student']]


#class QuestionMark(models.Model):



