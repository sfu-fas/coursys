from django import forms
from .models import Visa
from coredata.widgets import CalendarWidget
from coredata.forms import PersonField


class VisaForm(forms.ModelForm):
    person = PersonField()

    class Meta:
        exclude = []
        model = Visa
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget
            }

    def clean(self):
        cleaned_data = super(VisaForm, self).clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        print(end_date, type(end_date))
        if end_date is not None and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(VisaForm, self).is_valid(*args, **kwargs)