# Django
from django import forms
# Local
from coredata.widgets import PersonField, OfferingField, CalendarWidget
# App
from .models import TACategory, TAContract, TACourse
from .widgets import GuessPayperiodsWidget

class TACategoryForm(forms.ModelForm):
    class Meta:
        model = TACategory 

class TAContractForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        units = False
        if 'units' in kwargs:
            units = kwargs['units']
            del kwargs['units']
        super(TAContractForm, self).__init__(*args, **kwargs)
        if units:
            self.fields['category'].choices = [(obj.id, obj) for obj in \
                    TACategory.objects.visible(units)]

    person = PersonField()
    class Meta:
        model = TAContract
        widgets = {
            'pay_start':CalendarWidget,
            'pay_end':CalendarWidget,
            'deadline_for_acceptance':CalendarWidget,
            'payperiods':GuessPayperiodsWidget,
        }

class TACourseForm(forms.ModelForm):
    course = OfferingField()
    class Meta:
        model = TACourse
