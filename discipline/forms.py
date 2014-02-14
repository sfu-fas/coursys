from django import forms
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from discipline.models import *
from grades.models import Activity
from coredata.models import Member, Person
from groups.models import GroupMember
from submission.models import StudentSubmission, GroupSubmission
import itertools
import datetime

INPUT_WIDTH = 70

class DisciplineGroupForm(forms.ModelForm):
    students = forms.MultipleChoiceField(choices=[], required=False, widget=forms.SelectMultiple(attrs={'size': 15}))
    
    def __init__(self, offering, *args, **kwargs):
        super(DisciplineGroupForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
    
    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']
    
    class Meta:
        model = DisciplineGroup
        exclude = []
        widgets = {
            'offering': forms.HiddenInput(),
        }

class DisciplineCaseForm(forms.ModelForm):
    student = forms.ChoiceField(choices=[])

    def __init__(self, offering, *args, **kwargs):
        super(DisciplineCaseForm, self).__init__(*args, **kwargs)
        # store the course offering for validation
        self.offering = offering
    
    def clean_student(self):
        userid = self.cleaned_data['student']
        members = Member.objects.filter(offering=self.offering, person__userid=userid)
        if members.count() != 1:
            raise forms.ValidationError("Can't find student")

        return members[0].person
    
    class Meta:
        model = DisciplineCaseInstrStudent
        fields = ("student", "group")


class DisciplineInstrNonStudentCaseForm(forms.ModelForm):
    class Meta:
        model = DisciplineCaseInstrNonStudent
        fields = ("emplid", "userid", "email", "last_name", "first_name", "group")


class TemplateForm(forms.ModelForm):
    class Meta:
        model = DisciplineTemplate
        exclude = []
        widgets = {
            'text': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'20'}),
        }






class CaseNotesForm(forms.ModelForm):
    class Meta:
        model = DisciplineCaseBase
        fields = ("notes", "notes_public")
        widgets = {
            'notes': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'15'}),
            'notes_public': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'15'}),
        }
class CaseContactedForm(forms.ModelForm):
    def clean(self):
        contacted = self.cleaned_data['contacted']
        text = self.cleaned_data['contact_email_text']

        if contacted=="MAIL":
            if not text.strip():
                raise forms.ValidationError('Must enter email text: email is sent to student on submitting this form.')
            self.cleaned_data['contact_date'] = datetime.date.today()
            self.instance.send_contact_mail = True # trigger email sending in view logic
        elif contacted=="OTHR":
            if 'contact_date' not in self.cleaned_data or not self.cleaned_data['contact_date']:
                raise forms.ValidationError('Please enter the date of initial contact about the case.')

        return self.cleaned_data

    class Meta:
        model = DisciplineCaseBase
        fields = ("contacted", "contact_date", "contact_email_text")
        widgets = {
            'contacted': forms.RadioSelect(),
            'contact_email_text': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'15'}),
        }
class CaseResponseForm(forms.ModelForm):
    class Meta:
        model = DisciplineCaseBase
        fields = ("response",)
        widgets = {
            'response': forms.RadioSelect(),
        }
class CaseMeetingForm(forms.ModelForm):
    def clean_meeting_date(self):
        date = self.cleaned_data['meeting_date']
        if not date:
            return date
        if date > datetime.date.today():
            raise forms.ValidationError("Cannot select meeting/email date in the future.")
        return date

    class Meta:
        model = DisciplineCaseBase
        fields = ("meeting_date", "meeting_summary", "meeting_notes")
        widgets = {
            'meeting_summary': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
            'meeting_notes': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
        }
class CaseFactsForm(forms.ModelForm):
    class Meta:
        model = DisciplineCaseBase
        fields = ("facts",)
        widgets = {
            'facts': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'20'}),
        }
class CasePenaltyForm(forms.ModelForm):
    class Meta:
        model = DisciplineCaseBase
        fields = ("penalty", "refer", "penalty_reason")
        widgets = {
            'penalty': forms.RadioSelect(),
            'penalty_reason': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
        }
class CaseLetterReviewForm(forms.ModelForm):
    def clean_letter_review(self):
        review = self.cleaned_data['letter_review']
        if review:
            # cannot set to true if other required fields not filled in
            case = self.instance
            step = case.next_step()
            if step in PRE_LETTER_STEPS:
                raise forms.ValidationError(
                    mark_safe('Cannot finalize letter: have not entered <a href="%s">%s</a>.'
                        % (reverse('discipline.views.edit_case_info',
                            kwargs={'field': STEP_VIEW[step], 'course_slug':case.offering.slug, 'case_slug':case.slug}),
                        STEP_DESC[step])))

        return review

    class Meta:
        model = DisciplineCaseBase
        fields = ("letter_review",)

class CaseLetterSentForm(forms.ModelForm):
    def clean(self):
        letter_sent = self.cleaned_data.get('letter_sent', '')
        date = self.cleaned_data.get('letter_date', '')
        text = self.cleaned_data.get('letter_text', '')
        case = self.instance

        if letter_sent=="MAIL":
            if not case.letter_review:
                raise forms.ValidationError(
                    mark_safe('Cannot send letter: it has not <a href="%s">been reviewed</a>.'
                        % (reverse('discipline.views.edit_case_info',
                            kwargs={'field': 'letter_review', 'course_slug':case.offering.slug, 'case_slug':case.slug}))))
            self.instance.send_letter_now = True # trigger email sending in view logic
        elif letter_sent=="OTHR":
            if not text.strip():
                raise forms.ValidationError('Please enter details of the letter delivery.')
            if not date:
                raise forms.ValidationError('Please enter the date the letter was sent.')

        return self.cleaned_data

    class Meta:
        model = DisciplineCaseBase
        fields = ("letter_sent","letter_date","letter_text")
        widgets = {
            'letter_sent': forms.RadioSelect(),
        }

class CasePenaltyImplementedForm(forms.ModelForm):
    def clean_penalty_implemented(self):
        impl = self.cleaned_data['penalty_implemented']
        if impl and self.instance.penalty!="NONE" and self.instance.letter_sent=="WAIT":
            # cannot set to true if letter not sent
            raise forms.ValidationError(
                mark_safe('Cannot implement penalty: have not <a href="%s">sent letter</a>.'
                    % (reverse('discipline.views.edit_case_info',
                        kwargs={'field': 'letter_sent', 'course_slug':self.instance.offering.slug, 'case_slug':self.instance.slug}))))

        return impl

    class Meta:
        model = DisciplineCaseBase
        fields = ("penalty_implemented",)

"""
class CaseChairNotesForm(forms.ModelForm):
    class Meta:
        model = DisciplineCase
        fields = ("chair_notes",)
        widgets = {
            'chair_notes': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'20'}),
        }
class CaseChairMeetingForm(forms.ModelForm):
    def clean_chair_meeting_date(self):
        date = self.cleaned_data['chair_meeting_date']
        if date > datetime.date.today():
            raise forms.ValidationError("Cannot select meeting/email date in the future.")
        return date

    class Meta:
        model = DisciplineCase
        fields = ("chair_meeting_date", "chair_meeting_summary", "chair_meeting_notes")
        widgets = {
            'chair_meeting_summary': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
            'chair_meeting_notes': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
        }
class CaseChairFactsForm(forms.ModelForm):
    class Meta:
        model = DisciplineCase
        fields = ("chair_facts",)
        widgets = {
            'chair_facts': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'20'}),
        }
class CaseChairPenaltyForm(forms.ModelForm):
    class Meta:
        model = DisciplineCase
        fields = ("chair_penalty", "refer_ubsd", "chair_penalty_reason")
        widgets = {
            'chair_penalty': forms.RadioSelect(),
            'chair_penalty_reason': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'10'}),
        }
class CaseChairLetterReviewForm(forms.ModelForm):
    def clean_letter_review(self):
        review = self.cleaned_data['chair_letter_review']
        if review:
            # cannot set to true if other required fields not filled in
            case = self.instance
            step = case.chair_next_step()
            if step in CHAIR_STEPS:
                raise forms.ValidationError(
                    mark_safe('Cannot finalize letter: have not entered <a href="%s">%s</a>.'
                        % (reverse('discipline.views.edit_case_info',
                            kwargs={'field': STEP_VIEW[step], 'course_slug':case.offering.slug, 'case_slug':case.slug}),
                        STEP_DESC[step])))

        return review

    class Meta:
        model = DisciplineCase
        fields = ("chair_letter_review",)

"""

class CaseRelatedForm(forms.Form):
    activities = forms.MultipleChoiceField(label="Activities in the course", widget=forms.SelectMultiple(attrs={'size':'8'}), required=False)
    submissions = forms.MultipleChoiceField(label="Submissions by this student (or groups they are in)", widget=forms.SelectMultiple(attrs={'size':'8'}), required=False)
    students = forms.MultipleChoiceField(label="Students from the course (other than students in the case group)", widget=forms.SelectMultiple(attrs={'size':'8'}), required=False)
    
    def set_choices(self, course, case):
        """
        Set choices fields as appropriate to this case.
        """
        # set activity choices
        activity_choices = [(act.id, act.name) for act in Activity.objects.filter(offering=course, deleted=False)]
        self.fields['activities'].choices = activity_choices

        # set submission choices
        if isinstance(case.student, Person):
            gms = GroupMember.objects.filter(student__person=case.student)
            sub_sets = [StudentSubmission.objects.filter(activity__offering=course, member__person=case.student)]
        else:
            # for FakePerson in non-student cases: no submissions possible.
            gms = []
            sub_sets = []
        
        for gm in gms:
            sub_sets.append( GroupSubmission.objects.filter(activity=gm.activity, group=gm.group) )
        subs = itertools.chain(*sub_sets)
        submissions_choices = [(sub.id, "%s @ %s" % (sub.activity.name, sub.created_at.strftime("%Y-%m-%d %H:%M"))) for sub in subs]
        self.fields['submissions'].choices = submissions_choices
        
        # set student choices
        students_choices = [(m.id, m.person.sortname()) for m in Member.objects.filter(offering=course, role="STUD")]
        self.fields['students'].choices = students_choices


STEP_FORM = { # map of field -> form for editing it (all ModelForm for DisciplineCase, except Related)
        'notes': CaseNotesForm,
        'related': CaseRelatedForm,
        'contacted': CaseContactedForm,
        'response': CaseResponseForm,
        'meeting': CaseMeetingForm,
        'facts': CaseFactsForm,
        'penalty': CasePenaltyForm,
        'letter_review': CaseLetterReviewForm,
        'letter_sent': CaseLetterSentForm,
        'penalty_implemented': CasePenaltyImplementedForm,

        #'chair_notes': CaseChairNotesForm,
        #'chair_meeting': CaseChairMeetingForm,
        #'chair_facts': CaseChairFactsForm,
        #'chair_penalty': CaseChairPenaltyForm,
        #'chair_letter_review': CaseChairLetterReviewForm,
        }




class NewAttachFileForm(forms.ModelForm):
    def __init__(self, case, *args, **kwargs):
        super(NewAttachFileForm, self).__init__(*args, **kwargs)
        # force the right case into place
        self.case = case
        self.fields['case'].initial = case.id
    
    def clean_case(self):
        if self.cleaned_data['case'].id != self.case.id:
            raise forms.ValidationError("Wrong case.")
        return self.cleaned_data['case'].subclass()
    
    class Meta:
        model = CaseAttachment
        exclude = ['mediatype']
        widgets = {
            'case': forms.HiddenInput(),
        }

class EditAttachFileForm(forms.ModelForm):
    def clean_case(self):
        if self.cleaned_data['case'] != self.case:
            raise forms.ValidationError("Wrong case.")
        return self.cleaned_data['case']
    
    class Meta:
        model = CaseAttachment
        exclude = ['case', 'attachment', 'mediatype']

