import datetime

from coredata.models import Semester

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import TeachingAdjust
from faculty.event_types.fields import TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent


class NormalTeachingLoadHandler(CareerEventHandlerBase, TeachingCareerEvent):

    EVENT_TYPE = 'NORM_TEACH'
    NAME = 'Normal Teaching Load'

    IS_EXCLUSIVE = True
    SEMESTER_BIAS = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Required Load</dt><dd>{{ handler|get_config:'load' }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        load = TeachingCreditField(label='Teaching Load')

    def short_summary(self):
        load = self.get_config('load')
        return "I'm required to have a teaching load of {}".format(load)

    def teaching_adjust_per_semester(self):
        load = self.get_config('load')
        # XXX: Normally it's (credits, load_decrease) so if I want a load increase then
        #      load_decrease should be negated?
        return TeachingAdjust(0, -load)


class OneInNineHandler(CareerEventHandlerBase, TeachingCareerEvent):

    EVENT_TYPE = 'ONE_NINE'
    NAME = 'One-in-Nine Semester'

    IS_INSTANT = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Teaching Credit Given</dt><dd>{{ handler|get_config:'credit' }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        credit = TeachingCreditField(label='Teaching Credit')

    @staticmethod
    def get_semester(date):
        semester_date = max(date, datetime.date(date.year, date.month, 5))
        return Semester.get_semester(semester_date)

    def pre_save(self):
        # This event lasts for an entire semester, so we should set the start and end times
        # appropriately.
        # XXX: The Semester objects start on the 5th day of the first month so we must do
        #      this hack to make sure we look up the correct semester.
        semester = self.get_semester(self.event.start_date)
        self.event.start_date, self.event.end_date = Semester.start_end_dates(semester)

    def to_html_context(self):
        return {'start': self.get_semester(self.event.start_date)}

    def short_summary(self):
        semester = self.get_semester(self.event.start_date)
        credit = self.get_config('credit')
        return 'One-in-Nine: {} for {} teaching credit'.format(semester, credit)

    def teaching_adjust_per_semester(self):
        credit = self.get_config('credit')
        return TeachingAdjust(credit, 0)
