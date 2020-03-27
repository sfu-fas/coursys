# TODO: override start/end times for special-case students (somehow)
# TODO: a QuestionMark model and the UI for TAs to enter marks

import datetime

from django.db import models
from django.shortcuts import resolve_url

from coredata.models import Member
from courselib.json_fields import JSONField, config_property
from grades.models import Activity


QUESTION_TYPE_CHOICES = [
    ('MC', 'Multiple Choice'),
    ('MCM', 'Multiple Choice, multiple answer'),
    ('SHOR', 'Short Answer'),
    ('LONG', 'Long Answer'),
    ('NUM', 'Numeric Answer'),
    ('FILE', 'File Upload'),
    ('INST', 'Instructions (students enter nothing)'),
]
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
        # q.config['intro_markup']: markup language used: see courselib/markup.py
        # q.config['intro_math']: page uses MathJax? (boolean)

    intro = config_property('intro', default='')
    intro_markup = config_property('intro_markup', default='creole')
    intro_math = config_property('intro_math', default=False)

    class Meta:
        verbose_name_plural = 'Quizzes'

    objects = VisibleStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.activity.offering.slug, activity_slug=self.activity.slug)


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    type = models.CharField(max_length=4, null=False, blank=False, choices=QUESTION_TYPE_CHOICES)
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    points = models.PositiveSmallIntegerField(default=0, null=False, blank=False)
    order = models.PositiveSmallIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # q.config['text']: question text
        # q.config['markup']: markup language used: see courselib/markup.py
        # q.config['math']: page uses MathJax? (boolean)
        # others as set by the .type (and corresponding QuestionType)

    markup = config_property('markup', default='markdown')
    math = config_property('math', default=False)

    class Meta:
        ordering = ['order']
        unique_together = [['quiz', 'order']]

    objects = VisibleStatusManager()


class QuestionAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    answer = JSONField(null=False, blank=False, default=dict)
    # format of .answer determined by the corresponding QuestionType

    class Meta:
        unique_together = [['question', 'student']]


#class QuestionMark(models.Model):



