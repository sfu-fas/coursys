from django import forms
from django.forms.models import modelformset_factory
from django.template import Template, TemplateSyntaxError
from django.utils.translation import ugettext as _

from coredata.models import Semester, Unit, Person

from faculty.event_types.fields import SemesterCodeField, TeachingCreditField, DollarInput
from faculty.models import CareerEvent
from faculty.models import DocumentAttachment
from faculty.models import FacultyMemberInfo
from faculty.models import Grant
from faculty.models import Memo
from faculty.models import MemoTemplate


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
    reason = forms.CharField(required=False, max_length=200, widget=forms.Textarea(attrs={'rows':2, 'cols':70,}))


def attachment_formset_factory():
    return modelformset_factory(DocumentAttachment, form=AttachmentForm, extra=1)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment
        exclude = ("career_event", "created_by")


class MemoTemplateForm(forms.ModelForm):
    class Meta:
        model = MemoTemplate
        exclude = ('created_by', 'event_type', 'hidden')

    def __init__(self, *args, **kwargs):
        super(MemoTemplateForm, self).__init__(*args, **kwargs)
        self.fields['subject'].widget.attrs['size'] = 50
        self.fields['template_text'].widget.attrs['rows'] = 20
        self.fields['template_text'].widget.attrs['cols'] = 50

    def clean_template_text(self):
        template_text = self.cleaned_data['template_text']
        try:
            Template(template_text)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
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
        keys = ['to_lines', 'from_lines', 'subject', 'sent_date', 'memo_text', 'cc_lines']
        keys.extend([k for k in self.fields.keyOrder if k not in keys])
        self.fields.keyOrder = keys


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
        all_units = [(unicode(u.label), unicode(u.informal_name())) for u in units]
        self.fields['category'].choices = [('all', 'All Units')] + all_units


class EventFilterForm(forms.Form):
    CATEGORIES = [
        ('all', 'All Events'),
        ('current', 'Current Events'),
        ('teach', 'Teaching-related'),
        ('salary', 'Salary-related'),
    ]
    category = forms.ChoiceField(choices=CATEGORIES, initial='current', widget=forms.RadioSelect())


class GrantForm(forms.ModelForm):
    def __init__(self, units, *args, **kwargs):
        self.units = units
        super(GrantForm, self).__init__(*args, **kwargs)
        self.fields['unit'].queryset = Unit.objects.filter(id__in=(u.id for u in units))
        self.fields['unit'].choices = [(unicode(u.id), unicode(u)) for u in units]
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
    semester = SemesterCodeField()

    def __init__(self, *args, **kwargs):
        super(AvailableCapacityForm, self).__init__(*args, **kwargs)
        if 'semester' not in self.data:
            self.data['semester'] = Semester.current().name


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
            'title': _('Mr., Mrs., Dr., etc'),
            'emergency_contact': _('Name, phone number, etc'),
        }
        widgets = {
            'birthday': forms.DateInput(attrs={'class': 'date-input'}),
        }
