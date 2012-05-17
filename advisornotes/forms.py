from advisornotes.models import AdvisorNote, NonStudent
from coredata.models import Person
from django import forms
from django.forms.models import ModelForm
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from grades.forms import _required_star

class AdvisorNoteForm(forms.ModelForm):
    class Meta:
        model = AdvisorNote
        exclude = ('hidden',)
        widgets = {
                'text': forms.Textarea(attrs={'cols': 80, 'rows': 25})
                }

class StudentSelect(forms.Select):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        """
        Render for jQueryUI autocomplete widget
        """
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(value)
        return mark_safe(u'<input%s />' % forms.widgets.flatatt(final_attrs))

class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 30}), help_text="Type to search for a student.", **kwargs)
    
    def to_python(self, value):
        try:
            st = Person.objects.get(emplid=value)
        except (ValueError, Person.DoesNotExist):
            raise forms.ValidationError("Could not find person's record.")
        return st
    
class StudentSearchForm(forms.Form):
    search = StudentField()

class NoteSearchForm(forms.Form):
    search = forms.CharField()

class NonStudentForm(ModelForm):
    first_name = forms.CharField(label=mark_safe('First name ' + _required_star))
    last_name = forms.CharField(label=mark_safe('Last name ' + _required_star))
    
    class Meta:
        model = NonStudent
        exclude=('config')