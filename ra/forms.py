from django import forms
from ra.models import RAAppointment, Account, Project
from coredata.models import Person
from coredata.forms import PersonField
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from grad.models import GradStudent

class RAForm(forms.ModelForm):
    person = PersonField(label='Hire')
    sin = forms.IntegerField(label='SIN', required=False)
    #scholarship = forms.ChoiceField(choices=((None, '---------'),), required=False, help_text='Used only if Hiring Category is "Scholarship".')

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RAForm, self).is_valid(*args, **kwargs)

    def clean_sin(self):
        sin = self.cleaned_data['sin']
        emplid = int(self['person'].value())
        gradstudents = GradStudent.objects.filter(person__emplid=emplid)
        for gradstudent in gradstudents:
            gradstudent.set_sin(sin)
            gradstudent.save()
        return sin

    def clean_hours(self):
        data = self.cleaned_data['hours']
        if int(data) > 70:
            raise forms.ValidationError("The maximum number of work hours is 70.")
        return data

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data 
        
    class Meta:
        model = RAAppointment
        exclude = ('config','offer_letter_text','deleted')

class RALetterForm(forms.ModelForm):
    class Meta:
        model = RAAppointment
        fields = ('offer_letter_text',)
        widgets = {
                   'offer_letter_text': forms.Textarea(attrs={'rows': 25, 'cols': 70}),
                   }


class StudentSelect(forms.Select):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            final_attrs['value'] = force_unicode(value)
        return mark_safe(u'<input%s />' % forms.widgets.flatatt(final_attrs))

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
    hiring_faculty = forms.ChoiceField(choices=[])
    account = forms.ChoiceField(choices=[])
    project = forms.ChoiceField(choices=[])

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        exclude = ('hidden',)

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('hidden',)
