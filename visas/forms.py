from django import forms
from .models import Visa
from coredata.widgets import CalendarWidget, PersonField


class VisaForm(forms.ModelForm):
    person = PersonField()

    class Meta:
        exclude = []
        model = Visa
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget
            }