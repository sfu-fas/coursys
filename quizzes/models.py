import datetime

from django.db import models

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


class Quiz(models.Model):
    activity = models.OneToOneField(Activity)
    start = models.DateTimeField()
    end = models.DateTimeField()
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # p.config['intro']: introductory text for the quiz
        # p.config['intro_markup']: markup language used: see courselib/markup.py
        # p.config['intro_math']: page uses MathJax? (boolean)

    intro = config_property('intro', default=True)
    intro_markup = config_property('intro_markup', default='markdown')
    intro_math = config_property('intro_math', default=False)

    class Meta:
        verbose_name_plural = 'Quizzes'


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    type = models.CharField(max_length=4, null=False, blank=False, choices=QUESTION_TYPE_CHOICES)
    points = models.PositiveSmallIntegerField(default=0, null=False, blank=False)
    order = models.PositiveSmallIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # p.config['text']: question text
        # p.config['markup']: markup language used: see courselib/markup.py
        # p.config['math']: page uses MathJax? (boolean)
        # others as set by the .type (and corresponding QuestionType)

    markup = config_property('markup', default='markdown')
    math = config_property('math', default=False)

    class Meta:
        ordering = ['order']
        unique_together = [['quiz', 'order']]


class QuestionAnswer(models.Model):
    question = models.ForeignKey(Question)
    student = models.ForeignKey(Member)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    answer = JSONField(null=False, blank=False, default=dict)
    # format of .answer determined by the corresponding QuestionType

    class Meta:
        unique_together = [['question', 'student']]





