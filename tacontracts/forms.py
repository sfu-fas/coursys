# Django
from django import forms
# Local
from coredata.widgets import PersonField, OfferingField, CalendarWidget
from coredata.models import Unit, Semester
from ra.models import Account
# App
from .models import HiringSemester, TACategory, TAContract, TACourse, CourseDescription


class GuessPayperiodsWidget(forms.TextInput):
    """
    A widget to guess at pay-periods.
    Assumes that you have fields named "pay_start", "pay_end", and "payperiods"
    """
    class Media:
        js = ('moment.min.js', 'js/tacontracts.js')


class HiringSemesterForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(HiringSemesterForm, self).__init__(*args, **kwargs)
        
        semesters = Semester.objects.all().order_by('-name')
        self.fields['semester'].queryset = semesters
        self.fields['semester'].empty_label = None

        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        model = HiringSemester
        exclude = []
        widgets = {
                    'deadline_for_acceptance': CalendarWidget,
                    'pay_start': CalendarWidget,
                    'pay_end': CalendarWidget,
                    'payperiods': GuessPayperiodsWidget,
                }


class TACategoryForm(forms.ModelForm):
    def __init__(self, unit, *args, **kwargs):
        super(TACategoryForm, self).__init__(*args, **kwargs)
        accounts = Account.objects.filter(unit=unit)
        self.fields['account'].queryset = accounts

    class Meta:
        model = TACategory
        exclude = []


class TAContractForm(forms.ModelForm):
    def __init__(self, hiring_semester, *args, **kwargs):
        super(TAContractForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = TACategory.objects.visible(hiring_semester)

    person = PersonField()
    class Meta:
        model = TAContract
        exclude = []
        widgets = {
            'appointment_start': CalendarWidget,
            'appointment_end': CalendarWidget,
            'pay_start': CalendarWidget,
            'pay_end': CalendarWidget,
            'deadline_for_acceptance': CalendarWidget,
            'payperiods': GuessPayperiodsWidget,
        }


class TACourseForm(forms.ModelForm):
    def __init__(self, semester, *args, **kwargs):
        super(TACourseForm, self).__init__(*args, **kwargs)
        self.fields['course'].widget.semester = semester
    
    course = OfferingField()
    class Meta:
        model = TACourse
        exclude = []

class EmailForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)
    sender = PersonField()


class CourseDescriptionForm(forms.ModelForm):
    class Meta:
        model = CourseDescription
        exclude = ('config','hidden')
