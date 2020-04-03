# TODO: a QuestionMark model and the UI for TAs to enter marks
# TODO: delete Quiz?

import datetime
from typing import Optional, Tuple

from django.db import models
from django.db.models import Max
from django.shortcuts import resolve_url
from django.utils.safestring import SafeText

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

    def answer_html(self) -> SafeText:
        helper = self.question.helper()
        return helper.to_html(self)


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


#class QuestionMark(models.Model):



