from models import OutreachEvent, OutreachEventRegistration
from django import forms
from coredata.models import Unit
from faculty.event_types.fields import DollarInput


class OutreachEventForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(OutreachEventForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = OutreachEvent
        field_classes = {
            'start_date': forms.SplitDateTimeField,
            'end_date': forms.SplitDateTimeField,
        }
        widgets = {
            'description': forms.Textarea,
            'resources': forms.Textarea,
            'location': forms.Textarea,
            'notes': forms.Textarea,
            'cost': DollarInput,
            'score': forms.NumberInput(attrs={'class': 'smallnumberinput'}),
            'start_date': forms.SplitDateTimeWidget,
            'end_date': forms.SplitDateTimeWidget,
        }

    def clean(self):
        cleaned_data = super(OutreachEventForm, self).clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if end_date is not None and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")


class OutreachEventRegistrationForm(forms.ModelForm):
    class Meta:
        exclude = ['event']
        model = OutreachEventRegistration
        widgets = {
            'notes': forms.Textarea,
            'contact': forms.Textarea,
        }
        labels = {
            'waiver': "Photo Waiver.  I hereby agree to <legalese>"
        }
