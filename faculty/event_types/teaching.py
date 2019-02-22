import datetime
from django.utils.safestring import mark_safe

from coredata.models import Semester

from faculty.event_types import search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import TeachingAdjust
from faculty.event_types.fields import TeachingCreditField, AnnualTeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent


class NormalTeachingLoadHandler(CareerEventHandlerBase, TeachingCareerEvent):

    EVENT_TYPE = 'NORM_TEACH'
    NAME = 'Normal Teaching Load'

    IS_EXCLUSIVE = True
    SEMESTER_BIAS = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Required Load</dt><dd>{{ handler|get_display:'load' }} course{{ handler|get_display:'load'|pluralize }} per year</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        load = AnnualTeachingCreditField(label='Teaching Load', help_text=mark_safe('Expected teaching load per year. May be a fraction like 5/2.'))

    SEARCH_RULES = {
        'load': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'load',
    ]

    def short_summary(self):
        load = self.get_config('load')
        return "Teaching load: {}/year".format(load*3)

    def get_load_display(self):
        # display as an annual value, while storing as semesterly
        return str(self.get_config('load', 0)*3)

    def teaching_adjust_per_semester(self):
        load = self.get_config('load')
        # Normally it's (credits, load_decrease) so if I want a load increase then
        # load_decrease should be negated!
        return TeachingAdjust(0, -load)


class OneInNineHandler(CareerEventHandlerBase, TeachingCareerEvent):

    EVENT_TYPE = 'ONE_NINE'
    NAME = 'One-in-Nine Semester'

    SEMESTER_PINNED = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Teaching Credit Given</dt><dd>{{ handler|get_display:'credit' }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        credit = TeachingCreditField(label='Teaching Credit', initial=2)

    SEARCH_RULES = {
        'credit': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'credit',
    ]

    @staticmethod
    def get_semester(date):
        semester_date = max(date, datetime.date(date.year, date.month, 5))
        return Semester.get_semester(semester_date)

    def short_summary(self):
        semester = self.get_semester(self.event.start_date)
        return 'One-in-Nine Semester ({})'.format(semester.name)

    def teaching_adjust_per_semester(self):
        credit = self.get_config('credit')
        return TeachingAdjust(credit, 0)
