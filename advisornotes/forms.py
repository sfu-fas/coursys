from advisornotes.models import AdvisorNote, NonStudent
from coredata.models import Person
from django import forms
from django.forms.models import ModelForm
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from grades.forms import _required_star
from django.core import validators
from django.core.exceptions import ValidationError

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
            return st
        except:
            pass
        
        try:
            st = NonStudent.objects.get(slug=value)
        except (ValueError, NonStudent.DoesNotExist):
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
        exclude=('config', 'notes')
        
class MergeStudentField(forms.Field):
    
    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            raise ValidationError(self.error_messages['required'])
        try:
            value = int(value)
        except ValueError:
            raise forms.ValidationError("Invalid format")
        try:
            student = Person.objects.get(emplid=value)
        except Person.DoesNotExist:
            raise forms.ValidationError("Could not find student record")
        return student
    
class MergeStudentForm(forms.Form):
    
    student = MergeStudentField(label="Student #")
    
    
    
    