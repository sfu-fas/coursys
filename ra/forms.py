from django import forms
from ra.models import RAAppointment, Account, Project, HIRING_CATEGORY_DISABLED, RAAppointmentAttachment, Program
from coredata.models import Person, Semester, Unit
from coredata.forms import PersonField
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text


class RAForm(forms.ModelForm):
    person = PersonField(label='Hire')
    sin = forms.IntegerField(label='SIN', required=False)
    use_hourly = forms.BooleanField(label='Use Hourly Rate', initial=False, required=False,
                                    help_text='Should the hourly rate be displayed on the contract (or total hours for lump sum contracts)?')

    class Meta:
        model = RAAppointment
        exclude = ('config','offer_letter_text','deleted')

    def __init__(self, *args, **kwargs):
        super(RAForm, self).__init__(*args, **kwargs)
        choices = self.fields['hiring_category'].choices
        choices = [(k,v) for k,v in choices if k not in HIRING_CATEGORY_DISABLED]
        self.fields['hiring_category'].choices = choices

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RAForm, self).is_valid(*args, **kwargs)

    def clean_sin(self):
        sin = self.cleaned_data['sin']
        try:
            emplid = int(self['person'].value())
        except ValueError:
            raise forms.ValidationError("The correct format for a SIN is XXXXXXXXX, all numbers, no spaces or dashes.")
        people = Person.objects.filter(emplid=emplid)
        if people:
            person = people[0]
            person.set_sin(sin)
            person.save()
        return sin

    def clean_hours(self):
        data = self.cleaned_data['hours']
        if self.cleaned_data['pay_frequency'] == 'L':
            return data

        if int(data) > 168:
            raise forms.ValidationError("There are only 168 hours in a week.")
        if int(data) < 0:
            raise forms.ValidationError("One cannot work negative hours.")
        return data

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data 
        

class RALetterForm(forms.ModelForm):
    class Meta:
        model = RAAppointment
        fields = ('offer_letter_text',)
        widgets = {
                   'offer_letter_text': forms.Textarea(attrs={'rows': 25, 'cols': 70}),
                   }


class LetterSelectForm(forms.Form):
    letter_choice = forms.ChoiceField(label='Select a letter', required=True, help_text='Please select the appropriate letter template for this RA.')

    def __init__(self, choices=[], *args, **kwargs):
        super(LetterSelectForm, self).__init__(*args, **kwargs)
        self.fields["letter_choice"].choices = choices


class StudentSelect(forms.Select):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            final_attrs['value'] = force_text(value)
        return mark_safe('<input%s />' % forms.widgets.flatatt(final_attrs))

class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 30}), help_text="Type to search for a student's appointments.", **kwargs)

    def to_python(self, value):
        try:
            st= Person.objects.get(emplid=value)
        except (ValueError, Person.DoesNotExist):
            raise forms.ValidationError("Unknown person selected")
        return st


class RASearchForm(forms.Form):
    search = StudentField()


class RABrowseForm(forms.Form):
    current = forms.BooleanField(label='Only current appointments', initial=True, help_text='Appointments active now (or within two weeks).')


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        exclude = ('hidden',)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('hidden',)
        widgets = {
            'project_prefix': forms.TextInput(attrs={'size': 1})
        }


class SemesterConfigForm(forms.Form):
    unit = forms.ModelChoiceField(queryset=Unit.objects.all())
    start_date = forms.DateField(required=True, help_text="Default start date for contracts")
    end_date = forms.DateField(required=True, help_text="Default end date for contracts")


class RAAppointmentAttachmentForm(forms.ModelForm):
    class Meta:
        model = RAAppointmentAttachment
        exclude = ('appointment', 'created_by')


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        exclude = ('hidden',)
