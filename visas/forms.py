from django import forms
from .models import Visa
from coredata.widgets import CalendarWidget, PersonField

class VisaForm(forms.ModelForm):
    class Meta:
        exclude = []
        model = Visa
        person = PersonField()
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget
            }