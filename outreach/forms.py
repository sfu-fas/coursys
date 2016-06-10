from models import OutreachEvent, OutreachEventRegistration
from django import forms
from coredata.models import Unit
from faculty.event_types.fields import DollarInput


class OutreachEventForm(forms.ModelForm):
    start_date = forms.SplitDateTimeField()
    end_date = forms.SplitDateTimeField()
    def __init__(self, request, *args, **kwargs):
        super(OutreachEventForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = OutreachEvent
        widgets = {
            'description': forms.Textarea,
            'resources': forms.Textarea,
            'cost': DollarInput,
            'score': forms.NumberInput(attrs={'class': 'smallnumberinput'})
        }


class OutreachEventRegistrationForm(forms.ModelForm):
    class Meta:
        exclude = ['event']
        model = OutreachEventRegistration
        widgets = {
            'notes': forms.Textarea,
            'contact': forms.Textarea,
        }
