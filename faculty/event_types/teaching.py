import fractions

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
