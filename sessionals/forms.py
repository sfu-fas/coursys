from django import forms
from .models import SessionalContract, SessionalAccount, SessionalConfig
from coredata.widgets import CalendarWidget, OfferingField
from coredata.forms import PersonField
from coredata.models import Unit
from coredata.widgets import DollarInput


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

    def clean(self):
        cleaned_data = super(SessionalAccountForm, self).clean()
        position_number = cleaned_data.get('position_number')
        if position_number and len(str(position_number)) > 9:
            raise forms.ValidationError({'position_number': "Position number cannot be more than 9 characters if it "
                                                            "is to fit in the payroll form."})


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
            'total_salary': DollarInput,
            'appt_guarantee': forms.RadioSelect,
            'appt_type': forms.RadioSelect
        }
        help_texts = {
            'notes': 'These will appear in the "Remarks" field of the payroll form.'
        }
        fields = ['person', 'account', 'unit', 'sin', 'visa_verified', 'appointment_start', 'appointment_end',
                  'pay_start', 'pay_end', 'offering', 'course_hours_breakdown','appt_guarantee', 'appt_type',
                  'contact_hours', 'total_salary', 'notes']

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
        sin = cleaned_data.get("sin")
        if sin and len(sin) != 9:
            raise forms.ValidationError({'sin': "SIN has to be exactly 9 digits."})


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