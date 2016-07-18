from django import forms
from .models import SessionalContract, SessionalAccount, SessionalConfig
from coredata.widgets import CalendarWidget, AutocompleteOfferingWidget, OfferingField
from coredata.forms import PersonField
from coredata.models import Unit


class SessionalAccountForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(SessionalAccountForm, self).__init__(*args, **kwargs)
        #  The following two lines look stupid, but they are not.  request.units contains a set of units.
        #  in order to be used this way, we need an actual queryset.
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = SessionalAccount


class SessionalContractForm(forms.ModelForm):
    person = PersonField()
    offering = OfferingField()

    def __init__(self, request, *args, **kwargs):
        super(SessionalContractForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        accounts = SessionalAccount.objects.visible(units)
        self.fields['account'].queryset = accounts
        self.fields['account'].empty_label = None
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = ['sessional']
        model = SessionalContract
        widgets = {
            'pay_start': CalendarWidget,
            'pay_end': CalendarWidget,
            'appointment_start': CalendarWidget,
            'appointment_end': CalendarWidget,
            'contract_hours': forms.NumberInput(attrs={'class': 'smallnumberinput'}),
            'notes': forms.Textarea
        }
        fields = ['person', 'account', 'unit', 'sin', 'visa_verified', 'appointment_start', 'appointment_end', 'pay_start',
                  'pay_end', 'offering', 'contract_hours', 'notes']

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(SessionalContractForm, self).is_valid(*args, **kwargs)

    def clean(self):
        cleaned_data = super(SessionalContractForm, self).clean()
        appointment_start = cleaned_data.get("appointment_start")
        appointment_end = cleaned_data.get("appointment_end")
        if appointment_end < appointment_start:
            raise forms.ValidationError({'appointment_end': "Appointment end date cannot be before appointment start "
                                                            "date.",
                                         'appointment_start': "Appointment end date cannot be before appointmentstart "
                                                              "date."})
        pay_start = cleaned_data.get("pay_start")
        pay_end = cleaned_data.get("pay_end")
        if pay_end < pay_start:
            raise forms.ValidationError({'pay_end': "Pay end date cannot be before pay start date.",
                                         'pay_start': "Pay end date cannot be before pay start date."})


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