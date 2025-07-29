from typing import Iterable

from advisornotes.models import AdvisorNote, Announcement, NonStudent, ArtifactNote, Artifact, AdvisorVisit, AdvisorVisitCategory, AdvisorVisitSurvey, \
SURVEY_TIME_CHOICES, SURVEY_OVERALL_CHOICES, SURVEY_REASON_CHOICES, SURVEY_QUESTIONS_ANSWERED_CHOICES, SURVEY_SUPPORT_CHOICES, SURVEY_ADVISOR_REVIEW_CHOICES, SURVEY_QUESTIONS_UNANSWERED_CHOICES
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

GENDER_CHOICES_NONSTUDENT = (
     ('', 'Prefer not to answer'),
     ('M', 'Male'),
     ('F', 'Female'),
     ('X', 'Non-binary')
)

CAMPUS_CHOICES_NONSTUDENT = (
    ('', '--------'),
    ('Burnaby', 'Burnaby'),
    ('Surrey', 'Surrey'),
)

PROGRAM_CHOICES_NONSTUDENT = (
    ('', '--------'),
    ('CMPT', 'Computing Science'),
    ('ENSC', 'Engineering Science'),
    ('MSE', 'Mechatronic Systems Engineering'),
    ('SS', 'Software Systems'),
    ('SEE', 'Sustainable Energy Engineering'),
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
    email_address = forms.EmailField(required=True, label="Email Address")
    start_year = StartYearField(help_text="The predicted/potential start year", required=True, label="Start Year", widget=forms.TextInput())
    gender = forms.ChoiceField(choices= GENDER_CHOICES_NONSTUDENT, required=False)
    campus = forms.ChoiceField(label="Preferred Campus", choices=CAMPUS_CHOICES_NONSTUDENT, required=False)
    program = forms.ChoiceField(required=False, choices=PROGRAM_CHOICES_NONSTUDENT, label="Potential Program")
    first_name = forms.CharField(label="Preferred First Name")
    last_name = forms.CharField(label="Last Name")
    middle_name = forms.CharField(label="Middle Name", required=False)
    high_school = forms.CharField(label="High School", required=False)

    class Meta:
        model = NonStudent
        exclude = ('config', 'notes', 'created_at', 'pref_first_name')

    field_order = ['first_name', 'last_name', 'middle_name', 'gender', 'email_address', 
                   'high_school', 'college', 'start_year', 'unit', 'program', 'preferred_campus']

    def __init__(self, *args, **kwargs):
        super(NonStudentForm, self).__init__(*args, **kwargs)
        config_init = ['program', 'campus', 'gender']  
        self.fields['unit'].help_text = "The ownership unit for this prospective student"
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
    
    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['program', 'campus', 'gender']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])


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
    
class StudentSurveyForm(ModelForm):
    time = forms.ChoiceField(required=True, widget=forms.RadioSelect(), choices=SURVEY_TIME_CHOICES, label="Was 15 minutes enough time for your appointment?") 
    overall = forms.ChoiceField(required=True, widget=forms.RadioSelect(), choices=SURVEY_OVERALL_CHOICES, label="How would you rate your appointment overall?")
    reason = forms.MultipleChoiceField(required=True, widget=forms.CheckboxSelectMultiple(), choices=SURVEY_REASON_CHOICES, label="Why did you meet with an advisor?")
    questions_answered = forms.ChoiceField(required=True, widget=forms.RadioSelect(), choices=SURVEY_QUESTIONS_ANSWERED_CHOICES, label="Did the advisor answer your question(s)?")
    support = forms.ChoiceField(required=True, widget=forms.RadioSelect(), choices=SURVEY_SUPPORT_CHOICES, label="I felt supported during my advising appointment?")
    advisor_review = forms.MultipleChoiceField(required=True, widget=forms.CheckboxSelectMultiple(), choices=SURVEY_ADVISOR_REVIEW_CHOICES, label="The advisor… (select all that apply)")
    questions_unanswered = forms.ChoiceField(required=True, widget=forms.RadioSelect(), choices=(('none', 'N/A - The advisor fully answered my questions'),)  + SURVEY_QUESTIONS_UNANSWERED_CHOICES, label="If your question wasn't fully answered during your appointment, what was the main reason? (Select the option that best describes your experience) ")
    comments = forms.CharField(required=False, label="Any other comments? (Optional)", widget=forms.Textarea(attrs={'rows': 5}), max_length=500, help_text="Maximum 500 Characters")

    # extra info
    other_questions_unanswered = forms.CharField(required=False, label="", widget=forms.Textarea(attrs={'rows': 2}), max_length=200, help_text="Maximum 200 Characters")
    other_advisor_review = forms.CharField(required=False, label="", widget=forms.Textarea(attrs={'rows': 2}), max_length=200, help_text="Maximum 200 Characters")
    other_reason = forms.CharField(required=False, label="", widget=forms.Textarea(attrs={'rows': 2}), max_length=200, help_text="Maximum 200 Characters")

    class Meta:
        model = AdvisorVisitSurvey
        fields = ['time', 'overall', 'reason', 'questions_answered', 'support', 'advisor_review', 'questions_unanswered', 'comments']

    field_order = ['time', 'overall', 'reason', 'other_reason', 'questions_answered', 'support', 'advisor_review', 'other_advisor_review', 'questions_unanswered', 'other_questions_unanswered', 'comments']

    def clean_advisor_review(self):
        return ",".join(self.cleaned_data['advisor_review'])
    
    def clean_reason(self):
        return ",".join(self.cleaned_data['reason'])
    
    def clean_questions_unanswered(self):
        value = self.cleaned_data['questions_unanswered']
        if self.cleaned_data['questions_unanswered'] == 'none':
            return None
        else:
            return value

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['other_questions_unanswered', 'other_advisor_review', 'other_reason']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        if 'advisor_review' or 'reason' in self.errors: 
            return cleaned_data

        questions_unanswered = cleaned_data.get('questions_unanswered')
        advisor_review = cleaned_data.get('advisor_review')
        reason = cleaned_data.get('reason')

        if questions_unanswered and questions_unanswered != "OT": 
            setattr(self.instance, 'other_questions_unanswered', '')
        if advisor_review and "OT" not in advisor_review.split(","): 
            setattr(self.instance, 'other_advisor_review', '')
        if reason and "OT" not in reason.split(","):
            setattr(self.instance, 'other_reason', '')