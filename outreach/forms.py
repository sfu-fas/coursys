from models import OutreachEvent, OutreachEventRegistration
from django import forms
from coredata.widgets import CalendarWidget
from coredata.models import Unit


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
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget,
            'description': forms.Textarea
        }


class OutreachEventRegistrationForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(OutreachEventRegistrationForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['event'].queryset = OutreachEvent.visible(units)
        self.fields['event'].empty_label = None

    class Meta:
        exclude = []
        model = OutreachEventRegistration
