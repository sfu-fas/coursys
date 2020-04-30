from django import forms

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.choices import Choices
from faculty.event_types.base import TeachingAdjust
from faculty.event_types.fields import TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent
from faculty.event_types.search import ChoiceSearchRule
from faculty.event_types.search import ComparableSearchRule


class AdminPositionEventHandler(CareerEventHandlerBase, TeachingCareerEvent):
    """
    Given admin position
    """

    EVENT_TYPE = 'ADMINPOS'
    NAME = 'Admin Position'

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Position</dt><dd>{{ handler|get_display:'position' }}</dd>
        <dt>Teaching Credit</dt><dd>{{ handler|get_display:'teaching_credit' }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        POSITIONS = Choices(
            ('UGRAD_DIRECTOR', 'Undergrad Program Director'),
            ('GRAD_DIRECTOR', 'Graduate Program Director'),
            ('DDP_DIRECTOR', 'Dual-Degree Program Director'),
            ('ASSOC_DIRECTOR', 'Associate Director/Chair'),
            ('DIRECTOR', 'School Director/Chair'),
            ('ASSOC_DEAN', 'Associate Dean'),
            ('DEAN', 'Dean'),
            ('OTHER', 'Other Admin Position'),
        )

        position = forms.ChoiceField(required=True, choices=POSITIONS)
        teaching_credit = TeachingCreditField(required=False, initial=None)

    SEARCH_RULES = {
        'position': ChoiceSearchRule,
        'teaching_credit': ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'position',
        'teaching_credit',
    ]

    def get_position_display(self):
        return self.EntryForm.POSITIONS.get(self.get_config('position'), 'N/A')

    def get_teaching_credit_display(self):
        return self.get_config('teaching_credit', default='N/A')

    @classmethod
    def default_title(cls):
        return 'Admin Position'

    def short_summary(self):
        position = self.get_position_display()
        return 'Admin Position: {0}'.format(position)

    def teaching_adjust_per_semester(self):
        credit = self.get_config('teaching_credit', 0)
        return TeachingAdjust(credit, 0)
