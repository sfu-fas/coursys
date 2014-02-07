import fractions

from django import forms

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices
from faculty.event_types.base import TeachingAdjust
from faculty.event_types.fields import TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent


class AdminPositionEventHandler(CareerEventHandlerBase, TeachingCareerEvent):
    """
    Given admin position
    """
    EVENT_TYPE = 'ADMINPOS'
    NAME = 'Admin Position'

    class EntryForm(BaseEntryForm):

        POSITIONS = Choices(
            ('DEAN', 'Dean'),
            ('UGRAD_DIRECTOR', 'Undergrad Director'),
        )

        position = forms.ChoiceField(required=True, choices=POSITIONS)
        teaching_credit = TeachingCreditField(required=False)

    @classmethod
    def default_title(cls):
        return 'Admin Position'

    def short_summary(self):
        position = self.EntryForm.POSITIONS.get(self.get_config('position'), 'N/A')
        return 'Given position: {}'.format(position)

    def teaching_adjust_per_semester(self):
        adjust = fractions.Fraction(self.event.config.get('teaching_credit', 0) or 0)
        return TeachingAdjust(adjust, adjust)
