from typing import Iterable

from advisornotes.models import AdvisorNote, Announcement, NonStudent, ArtifactNote, Artifact, AdvisorVisit, AdvisorVisitCategory
from coredata.models import Person, Unit
from coredata.forms import OfferingField, CourseField
from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.models import ModelForm
from courselib.markup import MarkupContentMixin, MarkupContentField
import datetime

TEXT_WIDTH = 70

ADVISING_CAMPUS_FORM_CHOICES = (
        ('BRNBY', 'Burnaby'),
        ('SURRY', 'Surrey'),
        ('OFFCA', 'Off-Campus')
        )

ADVISING_MODE_FORM_CHOICES = (
        ('IP', 'In-Person'),
        ('R', 'Remote'),
    )

class AdvisorNoteForm(MarkupContentMixin(field_name='text'), forms.ModelForm):
    text = MarkupContentField(label="Content", default_markup='plain', allow_math=False, restricted=False, with_wysiwyg=True)
    email_student = forms.BooleanField(required=False,
                                       help_text="Should the student be emailed the contents of this note?")

    def __init__(self, student, *args, **kwargs):
        # Only needed for the clean_email_student below, so that we may check for an email and display a validation
        # error if needed.  The view handles sending the actual email afterwards.
        self.student = student
        super().__init__(*args, **kwargs)

    def clean_email_student(self):
        email = self.cleaned_data['email_student']
        if email and not self.student.email():
            raise ValidationError("We don't have an email address for this student: cannot email them here.")
        return email

    class Meta:
        model = AdvisorNote
        exclude = ('hidden', 'emailed', 'created_at', 'config')


class AnnouncementForm(MarkupContentMixin(field_name='message'), forms.ModelForm):
    message = MarkupContentField(default_markup='plain', allow_math=False, restricted=False, with_wysiwyg=True)

    class Meta:
        model = Announcement
        exclude = ('hidden', 'author','created_at', 'config')

    def __init__(self, units: Iterable[Unit], *args, **kwargs):
        super().__init__(*args, **kwargs)
        # force unit choice to be as specified:
        self.fields['unit'].queryset = Unit.objects.filter(id__in=(u.id for u in units))
        self.fields['unit'].empty_label = None


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

class StudentSelect(forms.TextInput):
    pass


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


class ArtifactSearchForm(forms.Form):
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


class AdvisorVisitCategoryForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(AdvisorVisitCategoryForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        model = AdvisorVisitCategory
        exclude = []


class AdvisorVisitFormInitial(forms.ModelForm):
    programs = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '50', 'rows': '5'}),
                               help_text='This field can not be edited.  To refresh it, click "Refresh SIMS info".')

    cgpa = forms.CharField(label='CGPA', widget=forms.TextInput(attrs={'size': 4}),
                           required=False, help_text='This field can not be edited.  To refresh it, click "Refresh '
                                                     'SIMS info".')
    credits = forms.CharField(required=False, widget=forms.TextInput(attrs={'size': 4}),
                              help_text='This field can not be edited.  To refresh it, click "Refresh SIMS info".')

    gender = forms.CharField(required=False, widget=forms.TextInput(attrs={'size': 1}),
                              help_text='This field can not be edited.  To refresh it, click "Refresh SIMS info".')

    citizenship = forms.CharField(required=False, widget=forms.TextInput(attrs={'size': 10}),
                              help_text='This field can not be edited.  To refresh it, click "Refresh SIMS info".')
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'cols': '70', 'rows': '5'}),
                           help_text='If you want to also create a note, please type its content here.  This is a '
                                     'plain text note.  If you want more fancy formatting, please create a note in '
                                     'the main student notes page.')
    file_attachment = forms.FileField(required=False,
                                      help_text="If you add a note, you may also add an attachment to it.")
    email_student = forms.BooleanField(required=False,
                                       help_text="Should the student be emailed the contents of this note?")

    def __init__(self, *args, **kwargs):
        super(AdvisorVisitFormInitial, self).__init__(*args, **kwargs)
        categories = AdvisorVisitCategory.objects.visible([self.instance.unit])
        self.fields['categories'].queryset = categories
        initial = kwargs.setdefault('initial', {})
        initial['categories'] = [c.pk for c in kwargs['instance'].categories.all()]
        self.fields['programs'].widget.attrs['readonly'] = True
        self.fields['credits'].widget.attrs['readonly'] = True
        self.fields['cgpa'].widget.attrs['readonly'] = True
        self.fields['gender'].widget.attrs['readonly'] = True
        self.fields['citizenship'].widget.attrs['readonly'] = True
        # You have to manually reset the choices for the widget not to have the blank line.
        self.fields['mode'].widget.choices = ADVISING_MODE_FORM_CHOICES
        self.fields['campus'].widget.choices = ADVISING_CAMPUS_FORM_CHOICES
        self.fields['campus'].label = "Location"
        if categories.count() > 0:
            self.fields['categories'].required = True

    class Meta:
        model = AdvisorVisit
        fields = ['programs', "cgpa", "credits", "gender", "citizenship", "mode", "campus", "categories", "note",
                  "file_attachment", "email_student"]
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'mode': forms.RadioSelect(),
            'campus': forms.RadioSelect()
        }

    def clean_email_student(self):
        email = self.cleaned_data['email_student']
        if email and not self.instance.get_email():
            raise ValidationError("We don't have an email address for this student: cannot email them here.")
        return email

    def clean_note(self):
        text = self.cleaned_data['note']
        if 'file_attachment' in self.files and not text:
            raise ValidationError("You need to add a note in order to save an attachment.")
        return text


class AdvisorVisitFormSubsequent(forms.ModelForm):
    end_time = forms.SplitDateTimeField()

    def __init__(self, *args, **kwargs):
        super(AdvisorVisitFormSubsequent, self).__init__(*args, **kwargs)
        categories = AdvisorVisitCategory.objects.visible([self.instance.unit])
        self.fields['categories'].queryset = categories
        initial = kwargs.setdefault('initial', {})
        initial['categories'] = [c.pk for c in kwargs['instance'].categories.all()]
        # You have to manually reset the choices for the widget not to have the blank line.
        self.fields['mode'].widget.choices = ADVISING_MODE_FORM_CHOICES
        self.fields['campus'].widget.choices = ADVISING_CAMPUS_FORM_CHOICES
        self.fields['campus'].label = "Location"
        if categories.count() > 0:
            self.fields['categories'].required = True

    class Meta:
        model = AdvisorVisit
        fields = ["mode", "campus", "end_time", "categories"]
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'end_time': forms.SplitDateTimeWidget(),
            'mode': forms.RadioSelect(),
            'campus': forms.RadioSelect()
        }

    def clean_end_time(self):
        end_time = self.cleaned_data['end_time']
        if end_time and end_time <= self.instance.created_at:
            raise ValidationError("Cannot end the meeting before it started.")
        elif end_time and end_time > datetime.datetime.now():
            raise ValidationError("Cannot end a meeting in the future.")
        return end_time
