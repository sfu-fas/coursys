from django import forms
from django.forms.models import modelformset_factory
from django.template import Template, TemplateSyntaxError
from django.utils.translation import ugettext as _

from coredata.models import Semester, Unit, Person, Role, FuturePerson
from coredata.forms import PersonField
from coredata.widgets import DollarInput

from faculty.event_types.fields import SemesterCodeField, TeachingCreditField, FractionField, AddSalaryField, AddPayField, AnnualTeachingCreditField
from faculty.models import CareerEvent
from faculty.models import DocumentAttachment
from faculty.models import PositionDocumentAttachment
from faculty.models import FacultyMemberInfo
from faculty.models import Grant
from faculty.models import Memo
from faculty.models import MemoTemplate
from faculty.models import Position
from faculty.models import RANK_CHOICES
from faculty.util import ReportingSemester
from faculty.event_types.fields import SemesterField

from collections import OrderedDict


def career_event_factory(person, post_data=None, post_files=None):
    if post_data:
        return CareerEventForm(post_data, post_files)
    return CareerEventForm(initial={"person": person})

class CareerEventForm(forms.ModelForm):
    class Meta:
        model = CareerEvent
        # TODO flags field throws 'int not iterable' error maybe to do with BitField?
        exclude = ("config", "flags", "person",)


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = CareerEvent
        fields = ("status",)

class NewRoleForm(forms.ModelForm):
    person = PersonField(label="Emplid", help_text="or type to search")
    class Meta:
        model = Role
        exclude = ("config", "role", "expiry")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(NewRoleForm, self).is_valid(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data
        if 'person' not in data:
            raise forms.ValidationError("You must specify a person")
        person = data['person']
        unit = data['unit']
        self.old_role = None
        existing = Role.objects.filter(person=person, unit=unit, role='FAC')
        if existing.exists():
            self.old_role = existing[0]
        return super(NewRoleForm, self).clean()


class GetSalaryForm(forms.Form):
    date = forms.DateField()


class DateRangeForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class TeachingSummaryForm(forms.Form):
    start_semester = SemesterCodeField()
    end_semester = SemesterCodeField()


class TeachingCreditOverrideForm(forms.Form):
    teaching_credits = TeachingCreditField(help_text='May be a fraction eg. 2/3')
    reason = forms.CharField(required=False, max_length=70, widget=forms.TextInput(attrs={'size':70,}))


def attachment_formset_factory():
    return modelformset_factory(DocumentAttachment, form=AttachmentForm, extra=1)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment
        exclude = ("career_event", "created_by")

        widgets = {
            'contents': forms.ClearableFileInput(attrs={'multiple': True})
        }
        help_texts = {
            'contents': "You can enter one or multiple files.  Please note that multiple files will "
                        "have the same title if a title is provided."
        }


class PositionAttachmentForm(forms.ModelForm):
    class Meta:
        model = PositionDocumentAttachment
        exclude = ("position", "created_by")

        widgets = {
            'contents': forms.ClearableFileInput(attrs={'multiple': True})
        }
        help_texts = {
            'contents': "You can enter one or multiple files.  Please note that multiple files will "
                        "have the same title if a title is provided."
        }


class TextAttachmentForm(forms.ModelForm):
    text_contents = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': 15, 'cols': 70}))

    class Meta:
        model = DocumentAttachment
        exclude = ("career_event", "created_by", "contents")

class MemoTemplateForm(forms.ModelForm):
    class Meta:
        model = MemoTemplate
        exclude = ('created_by', 'event_type', 'hidden')

    def __init__(self, *args, **kwargs):
        super(MemoTemplateForm, self).__init__(*args, **kwargs)
        self.fields['default_from'].widget.attrs['size'] = 50
        self.fields['subject'].widget.attrs['size'] = 50
        self.fields['template_text'].widget.attrs['rows'] = 20
        self.fields['template_text'].widget.attrs['cols'] = 50

    def clean_template_text(self):
        template_text = self.cleaned_data['template_text']
        try:
            Template(template_text)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + str(e))
        return template_text

class MemoForm(forms.ModelForm):
    class Meta:
        model = Memo
        exclude = ('unit', 'from_person', 'created_by', 'config', 'template', 'career_event', 'hidden')

        widgets = {
                   'career_event': forms.HiddenInput(),
                   'to_lines': forms.TextInput(attrs={'size': 50}),
                   'from_lines': forms.TextInput(attrs={'size': 50}),
                   'memo_text': forms.Textarea(attrs={'rows':25, 'cols': 70}),
                   'subject': forms.Textarea(attrs={'rows':2, 'cols':70}),
                   'cc_lines': forms.Textarea(attrs={'rows':3, 'cols':50}),
                   }

    def __init__(self,*args, **kwargs):
        super(MemoForm, self).__init__(*args, **kwargs)
        # reorder the fields to the order of the printed memo
        assert isinstance(self.fields, OrderedDict)
        keys = ['to_lines', 'from_lines', 'subject', 'sent_date', 'memo_text', 'cc_lines']
        keys.extend([k for k in list(self.fields.keys()) if k not in keys])

        field_data = [(k,self.fields[k]) for k in keys]
        self.fields.clear()
        for k,v in field_data:
            self.fields[k] = v

class MemoFormWithUnit(MemoForm):
    class Meta(MemoForm.Meta):
        exclude = ('from_person', 'created_by', 'config', 'template', 'career_event', 'hidden')


class SearchForm(forms.Form):
    start_date = forms.DateField(label='Start Date', required=False,
                                 widget=forms.DateInput(attrs={'class': 'date-input'}))
    end_date = forms.DateField(label='End Date (inclusive)', required=False,
                               widget=forms.DateInput(attrs={'class': 'date-input'}))
    unit = forms.ModelChoiceField(queryset=Unit.objects.all(), required=False)
    only_current = forms.BooleanField(required=False)

class UnitFilterForm(forms.Form):
    """
    Form for filtering a table by units the user has access to

    1) Initialize the form in view with UnitFilterForm(units)
       Here, units = Unit.sub_units(request.units)

    2) In the template, {% include 'faculty/_unit_form.html' %} to render the form

    3) Add the necessary javascript to get the form working, see search_form.html as an example
       - The table rows need a unit label class name, ex: <tr class="{{ handler.event.unit.label }}">
       - initialize filtering:
        $('#filter-form').change( function() {
          event_filter_update('<table_id>');
        }).change();

    """

    CATEGORIES = [
        ('all', 'All Units'),
    ]
    category = forms.ChoiceField(choices=CATEGORIES, initial='all', widget=forms.RadioSelect())

    def __init__(self, units, *args, **kwargs):
        super(UnitFilterForm, self).__init__(*args, **kwargs)
        self.multiple_units = len(units) > 1
        all_units = [(str(u.label), str(u.informal_name())) for u in units]
        self.fields['category'].choices = [('all', 'All Units')] + all_units


class EventFilterForm(forms.Form):
    CATEGORIES = [
        ('all', 'All Events'),
        ('current', 'Current/Future'),
        ('teach', 'Teaching-related'),
        ('salary', 'Salary-related'),
    ]
    category = forms.ChoiceField(choices=CATEGORIES, initial='current', widget=forms.RadioSelect())


class GrantForm(forms.ModelForm):
    def __init__(self, units, *args, **kwargs):
        self.units = units
        super(GrantForm, self).__init__(*args, **kwargs)
        self.fields['unit'].queryset = Unit.objects.filter(id__in=(u.id for u in units))
        self.fields['unit'].choices = [(str(u.id), str(u)) for u in units]
        owners = Person.objects.filter(role__role__in=["ADMN", "FAC", "FUND"], role__unit__in=units).distinct()
        self.fields['owners'].queryset = owners

    class Meta:
        model = Grant
        fields = ['title', 'owners', 'start_date', 'expiry_date', 'initial', 'overhead', 'unit']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'date-input'}),
            'expiry_date': forms.DateInput(attrs={'class': 'date-input'}),
            'initial': DollarInput(),
            'overhead': DollarInput(),
        }


class GrantImportForm(forms.Form):
    file = forms.FileField()


class AvailableCapacityForm(forms.Form):

    start_semester = SemesterCodeField()
    end_semester = SemesterCodeField()

    def __init__(self, *args, **kwargs):
        super(AvailableCapacityForm, self).__init__(*args, **kwargs)
        self.data = dict(self.data)
        if 'start_semester' not in self.data:
            self.data['start_semester'] = ReportingSemester.current().prev().prev().code
        if 'end_semester' not in self.data:
            self.data['end_semester'] = ReportingSemester.current().code


class CourseAccreditationForm(forms.Form):

    OPERATOR_CHOICES = (
        ('AND', 'HAS ALL'),
        ('OR', 'HAS ANY'),
        ('NONE_OF', 'HAS NONE OF'),
    )

    start_semester = SemesterCodeField()
    end_semester = SemesterCodeField()
    operator = forms.ChoiceField(choices=OPERATOR_CHOICES, required=False, initial='AND')
    flag = forms.MultipleChoiceField(choices=[], required=False,
                                      widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        flags = kwargs.pop('flags', [])
        super(CourseAccreditationForm, self).__init__(*args, **kwargs)
        self.data = dict(self.data)
        if 'start_semester' not in self.data:
            self.data['start_semester'] = Semester.current().name
        if 'end_semester' not in self.data:
            self.data['end_semester'] = Semester.current().name
        self.fields['flag'].choices = flags


class FacultyMemberInfoForm(forms.ModelForm):

    class Meta:
        model = FacultyMemberInfo
        exclude = ('person', 'config')

        help_texts = {
            'title': _('"Mr", "Mrs", "Dr", etc'),
            'emergency_contact': _('Name, phone number, etc'),
        }
        widgets = {
            'title': forms.TextInput(attrs={'size': '3'}),
            'birthday': forms.DateInput(attrs={'class': 'date-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        if title.endswith('.'):
            title = title[:-1]
        return title


class PositionForm(forms.ModelForm):
    title = forms.CharField(required=True)
    projected_start_date = SemesterField(semester_start=True, required=True)
    teaching_load = AnnualTeachingCreditField(label="Teaching Load", required=False)
    base_salary = AddSalaryField(required=False)
    add_salary = AddSalaryField(label="Market Differential", required=False)
    add_pay = AddPayField(required=False)
    position_number = forms.CharField(max_length=6, required=True)
    rank = forms.ChoiceField(choices=RANK_CHOICES, required=False)
    step = forms.DecimalField(max_digits=3, decimal_places=1, required=False)

    class Meta:
        fields = ['title', 'projected_start_date', 'unit', 'position_number', 'percentage', 'rank', 'step',
                  'base_salary', 'add_salary', 'add_pay']
        model = Position
        widgets = {
            'position_number': forms.TextInput(attrs={'size': '6'})
            }


class PositionCredentialsForm(forms.ModelForm):
    degree1 = forms.CharField(max_length=12, help_text='These are the degrees to be inserted into the '
                                                       'Recommendation for Appointment Forms (AKA "Yellow Form"). '
                                                       ' List the highest degree first.', required=False,
                              label='Degree 1', widget=forms.TextInput(attrs={'size': '13'}))
    year1 = forms.CharField(max_length=5, required=False, label='Year 1', widget=forms.TextInput(attrs={'size': '5'}))
    institution1 = forms.CharField(max_length=25, required=False, label='Institution 1')
    location1 = forms.CharField(max_length=23, required=False, label='City/Country 1')
    degree2 = forms.CharField(max_length=12, required=False, label='Degree 2',
                              widget=forms.TextInput(attrs={'size': '13'}))
    year2 = forms.CharField(max_length=5, required=False, label='Year 2', widget=forms.TextInput(attrs={'size': '5'}))
    institution2 = forms.CharField(max_length=25, required=False, label='Institution 2')
    location2 = forms.CharField(max_length=23, required=False, label='City/Country 2')
    degree3 = forms.CharField(max_length=12, required=False, label='Degree 3',
                              widget=forms.TextInput(attrs={'size': '13'}))
    year3 = forms.CharField(max_length=5, required=False, label='Year 3', widget=forms.TextInput(attrs={'size': '5'}))
    institution3 = forms.CharField(max_length=25, required=False, label='Institution 3')
    location3 = forms.CharField(max_length=23, required=False, label='City/Country 3')
    teaching_semester_credits = forms.DecimalField(max_digits=3, decimal_places=0, required=False,
                                                   help_text='Number of teaching semester credits, for the tenure '
                                                   'track form')

    class Meta:
        fields = ['degree1', 'year1', 'location1', 'institution1',
                  'degree2', 'year2', 'location2', 'institution2',
                  'degree3', 'year3', 'location3', 'institution3',
                  'teaching_semester_credits']
        model = Position


class PositionPickerForm(forms.Form):
    position_choice = forms.ChoiceField(label='Select a position', required=True, help_text='Please select the position from which to fill the wizard.')

    def __init__(self, choices=[], *args, **kwargs):
        super(PositionPickerForm, self).__init__(*args, **kwargs)
        self.fields['position_choice'].choices = choices


class PositionPersonForm(forms.Form):
    person = PersonField(label="Emplid", help_text="or type to search")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(PositionPersonForm, self).is_valid(*args, **kwargs)



class FuturePersonForm(forms.ModelForm):
    first_name = forms.CharField(max_length=32)
    last_name = forms.CharField(max_length=32)
    middle_name = forms.CharField(max_length=32, required=False)
    pref_first_name = forms.CharField(max_length=32, required=False)
    title = forms.CharField(max_length=4, required=False)
    email = forms.EmailField(required=False)
    sin = forms.CharField(required=False, max_length=9, label='SIN')
    birthdate = forms.DateField(required=False, label='Date of Birth')
    gender = forms.ChoiceField(choices=(
            ('M', 'Male'),
            ('F', 'Female'),
            ('U', 'Unknown')),
            required=False, initial='AND',
            widget=forms.RadioSelect)

    class Meta:
        model = FuturePerson
        exclude = ['config']
        widgets = {
            'sin': forms.TextInput(attrs={'size': '9'})
        }
