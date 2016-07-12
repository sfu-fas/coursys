from django import forms
from .models import SessionalContract, SessionalAccount, SessionalConfig
from coredata.widgets import CalendarWidget
from coredata.models import Unit


#  TODO:  We need to create a split Person/AnyPerson widget so we can pick one or the other.

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


class SessionalConfigForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(SessionalConfigForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = SessionalConfig
        widgets = {
            'pay_start': CalendarWidget,
            'pay_end': CalendarWidget,
            'appointment_start': CalendarWidget,
            'appointment_end': CalendarWidget
        }

    def clean(self):
        cleaned_data = super(SessionalConfigForm, self).clean()
        pay_start = cleaned_data.get("pay_start")
        pay_end = cleaned_data.get("pay_end")
        if pay_end < pay_start:
            raise forms.ValidationError({'pay_end': "Pay end date cannot be before pay start date.",
                                         'pay_start': "Pay end date cannot be before pay start date."})
        appointment_start = cleaned_data.get("appointment_start")
        appointment_end = cleaned_data.get("appointment_end")
        if appointment_end < appointment_start:
            raise forms.ValidationError({'appointment_end': "Appointment end date cannot be before appointment start "
                                                            "date.",
                                         'appointment_start': "Appointment end date cannot be before appointmentstart "
                                                             "date."})