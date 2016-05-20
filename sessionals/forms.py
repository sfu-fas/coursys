from django import forms
from .models import SessionalContract, SessionalAccount
from coredata.widgets import CalendarWidget
from coredata.models import Unit


class SessionalAccountForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(SessionalAccountForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = SessionalAccount


class SessionalContractForm(forms.ModelForm):

    class Meta:
        exclude = []
        model = SessionalContract
        widgets = {
            'pay_start': CalendarWidget,
            'pay_end': CalendarWidget,
            'appointment_start': CalendarWidget,
            'appointment_end': CalendarWidget
        }
