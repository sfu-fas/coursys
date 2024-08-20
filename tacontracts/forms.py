# Django
from django import forms
# Local
from coredata.widgets import PersonField, OfferingField, CalendarWidget
from coredata.models import Unit, Semester
from ra.models import Account
# App
from .models import HiringSemester, TACategory, TAContract, TACourse, CourseDescription, TAContractAttachment




class HiringSemesterForm(forms.ModelForm):
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':10, 'maxlength':625}))
    contact = forms.EmailField(required=False, label="Email Contact", help_text="Notification Email for Time Use Guidelines.")
    tssu_link = forms.URLField(required=False, label="Link to TSSU Collective Agreement", help_text="Link to TSSU Collective Agreement for Time Use Guidelines.")

    def __init__(self, request, *args, **kwargs):
        super(HiringSemesterForm, self).__init__(*args, **kwargs)
        
        semesters = Semester.objects.all().order_by('-name')
        self.fields['semester'].queryset = semesters
        self.fields['semester'].empty_label = None

        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

        self.initial['comments'] = getattr(self.instance, 'comments')
        self.initial['contact'] = getattr(self.instance, 'contact')
        self.initial['tssu_link'] = getattr(self.instance, 'tssu_link')

    def clean(self):
        cleaned_data = super().clean()
        setattr(self.instance, 'comments', cleaned_data['comments'])
        setattr(self.instance, 'contact', cleaned_data['contact'])
        setattr(self.instance, 'tssu_link', cleaned_data['tssu_link'])
        
    class Meta:
        model = HiringSemester
        exclude = []
        widgets = {
                    'deadline_for_acceptance': CalendarWidget,
                    'pay_start': CalendarWidget,
                    'pay_end': CalendarWidget,
                    'appointment_start': CalendarWidget,
                    'appointment_end': CalendarWidget,
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
        }


class TACourseForm(forms.ModelForm):
    def __init__(self, semester, *args, **kwargs):
        super(TACourseForm, self).__init__(*args, **kwargs)
        self.fields['course'].widget.semester = semester
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields['course'].widget.attrs['readonly'] = True
    
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


class TAContracttAttachmentForm(forms.ModelForm):
    class Meta:
        model = TAContractAttachment
        exclude = ('contract', 'created_by')