from advisornotes.models import AdvisorNote, NonStudent, ArtifactNote, Artifact
from coredata.models import Person
from coredata.forms import OfferingField, CourseField
from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.models import ModelForm
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
import datetime

TEXT_WIDTH = 70

class _AdvisorNoteForm(forms.ModelForm):

    email_student = forms.BooleanField(required=False,
                                       help_text="Should the student be emailed the contents of this note?")

    def clean_email_student(self):
        email = self.cleaned_data['email_student']
        if email and not self.student.email():
            raise ValidationError("We don't have an email address for this student: cannot email them here.")
        return email

    class Meta:
        model = AdvisorNote
        exclude = ('hidden', 'emailed', 'created_at', 'config')
        widgets = {'text': forms.Textarea(attrs={'cols': TEXT_WIDTH, 'rows': 15})}


def advisor_note_factory(student, post_data=None, files=None, initial=None, instance=None):
    """
    Factory method to return the proper form for a student/nonstudent
    """
    form = _AdvisorNoteForm(post_data, files, initial=initial, instance=instance)
    form.student = student
    return form

class ArtifactNoteForm(forms.ModelForm):
    class Meta:
        model = ArtifactNote
        exclude = ('hidden', 'course', 'course_offering', 'artifact',)
        widgets = {
                'text': forms.Textarea(attrs={'cols': TEXT_WIDTH, 'rows': 15})
                }


class EditArtifactNoteForm(forms.ModelForm):
    class Meta:
        model = ArtifactNote
        exclude = ('hidden', 'course', 'course_offering', 'artifact', 'category', 'text', 'file_attachment', 'unit',)
        widgets = {
                'text': forms.Textarea(attrs={'cols': TEXT_WIDTH, 'rows': 15})
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
        return mark_safe('<input%s />' % forms.widgets.flatatt(final_attrs))


class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 25}), help_text="Type to search for a student.", **kwargs)

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

class OfferingSearchForm(forms.Form):
    offering = OfferingField()
class CourseSearchForm(forms.Form):
    course = CourseField()

class StartYearField(forms.IntegerField):

    def validate(self, value):
        super(StartYearField, self).validate(value)
        if value is not None:
            super(StartYearField, self).validate(value)
            current_year = datetime.date.today().year
            if value < current_year:
                raise forms.ValidationError("Must be equal to or after %d" % current_year)


class NonStudentForm(ModelForm):
    start_year = StartYearField(help_text="The predicted/potential start year", required=True)

    class Meta:
        model = NonStudent
        exclude = ('config', 'notes')


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        exclude = ('config',)


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
    
