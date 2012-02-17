from django import forms
from ra.models import RAAppointment, Account, Project, \
                      HIRING_CATEGORY_CHOICES, PAY_TYPE_CHOICES
from coredata.models import Person, Role
#from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

class RAForm(forms.ModelForm):
    person = forms.CharField(label='Hire')
    units = forms.DecimalField(max_digits=6, decimal_places=3, label="Pay period units")

    def clean_person(self):
        return Person.objects.get(emplid=self.cleaned_data['person'])

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data 
        

    class Meta:
        model = RAAppointment
        exclude = ('config',)

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