from coredata.forms import UnitRoleForm
from courselib.markup import MarkupContentField
from django import forms
from discipline.models import DisciplineGroup, DisciplineCaseInstrStudent, DisciplineCaseInstrNonStudent, \
    DisciplineTemplate, DisciplineCaseBase, MAX_ATTACHMENTS, \
    CaseAttachment, INSTR_PENALTY_CHOICES, INSTR_PENALTY_VALUES, MAX_ATTACHMENTS_TEXT, MODE_CHOICES_MUST_ANSWER
from coredata.models import Member, Unit

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
        members = Member.objects.filter(offering=self.offering, person__userid=userid).exclude(role='DROP')
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
            'field': forms.Select(attrs={'autofocus': True}),
        }


class DisciplineRoleForm(UnitRoleForm):
    def __init__(self, *args, **kwargs):
        super(DisciplineRoleForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('DISC', 'Discipline Administrator: can view cases online'),
            ('DICC', 'Discipline Filer: receives reports by email')]
        univ_id = Unit.objects.get(label='UNIV').id
        self.fields['unit'].choices = [(u,l) for u,l in self.fields['unit'].choices if u != univ_id]


class CaseCentralNoteForm(forms.ModelForm):
    send = forms.BooleanField(label='Send email', required=False,
                              help_text='Should the updated letter be sent to the student and instructor?')

    class Meta:
        model = DisciplineCaseBase
        fields = ("central_note",)
        widgets = {
            'central_note': forms.Textarea(attrs={'cols':INPUT_WIDTH, 'rows':'5'}),
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

    def clean(self):
        cleaned_data = super().clean()
        case = cleaned_data['case']
        attach = cleaned_data['attachment']
        existing_attachments = CaseAttachment.objects.filter(case=case, public=True)
        existing_total = sum(a.attachment.size for a in existing_attachments)
        if existing_total + attach.size > MAX_ATTACHMENTS:
            self.add_error('attachment', 'Total size of attachments must be at most %s because of email limitations.'
                           % (MAX_ATTACHMENTS_TEXT,))

    class Meta:
        model = CaseAttachment
        fields = ['case', 'name', 'attachment']
        widgets = {
            'case': forms.HiddenInput(),
        }


class EditAttachFileForm(forms.ModelForm):
    def clean_case(self):
        if self.cleaned_data['case'] != self.case:
            raise forms.ValidationError("Wrong case.")
        return self.cleaned_data['case']

    def clean_name(self):
        name = self.cleaned_data['name']
        if CaseAttachment.objects.filter(name=name, case_id=self.instance.case_id).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Another attachment exists with this name.")
        return name

    class Meta:
        model = CaseAttachment
        exclude = ['case', 'attachment', 'mediatype']


class CaseEditForm(forms.Form):
    also_for = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(), choices=[], required=False)

    def __init__(self, case, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case

        # collect templates
        templates = DisciplineTemplate.objects.filter(field__in=self.fields.keys())
        for f in self.fields.values():
            f.templates = []
        for t in templates:
            self.fields[t.field].templates.append(t)

        # fill in group members
        if case.group:
            group_ids = case.group.disciplinecasebase_set.exclude(pk=case.pk).values_list('id', flat=True)
            groupmembers = list(DisciplineCaseInstrStudent.objects.filter(id__in=group_ids))
            groupmembers.extend(DisciplineCaseInstrNonStudent.objects.filter(id__in=group_ids))
            if 'also_for' in self.fields:
                self.fields['also_for'].choices = [(c.id, c.full_name()) for c in groupmembers]
            self.groupmembers = groupmembers
        else:
            self.groupmembers = []

    def clean_also_for(self):
        values = self.cleaned_data['also_for']
        return [c for c in self.groupmembers if str(c.id) in values]


class NotifyEmailForm(CaseEditForm):
    contact_email_text = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': '25'}), help_text='This message will be sent to the student (CC you)')


class FactsForm(CaseEditForm):
    weight = forms.CharField(label="Weight of work", required=False, widget=forms.TextInput(attrs={'size': '60'}),
         help_text='The work in question and its weight in the course. (e.g. "two assignments worth 5% each", "40% final exam")')
    mode = forms.ChoiceField(choices=MODE_CHOICES_MUST_ANSWER, widget=forms.RadioSelect(), required=True,
         help_text='Type of work in this case. Used for statistics of cases: not included in the incident report.')
    facts = MarkupContentField(label="Description of the case", required=False, allow_math=False, with_wysiwyg=True)


class PenaltyForm(CaseEditForm):
    penalty = forms.MultipleChoiceField(required=True, widget=forms.CheckboxSelectMultiple(), choices=INSTR_PENALTY_CHOICES)
    refer = forms.BooleanField(required=False, label='Refer to chair?',
                               help_text='Refer this case to the Chair/Director for further penalty?')
    penalty_reason = MarkupContentField(label="Additional explanation/rationale (optional)", required=False, allow_math=False,
                                        with_wysiwyg=True, rows=5)

    def clean_penalty(self):
        penalties = self.cleaned_data['penalty']
        if set(penalties) - INSTR_PENALTY_VALUES:
            raise forms.ValidationError('illegal values in penalty submission')
        if 'WAIT' in penalties and len(penalties) > 1:
            raise forms.ValidationError('"not assigned" incompatible with other penalty values')
        if 'NONE' in penalties and len(penalties) > 1:
            raise forms.ValidationError('"no penalty" incompatible with other penalty values')
        return ','.join(penalties)


class SendForm(CaseEditForm):
    letter_review = forms.BooleanField(required=True, label='Report is ready to send',
        help_text='Have you reviewed the incident report, and confirmed that it is ready to send?')
    also_for = None

    def clean_letter_review(self):
        r = self.cleaned_data['letter_review']
        if not self.case.sendable():
            raise forms.ValidationError('Cannot send letter: some steps not complete.')
        return r


class NotesForm(CaseEditForm):
    notes = MarkupContentField(label="Additional notes", required=False, allow_math=False, with_wysiwyg=True, rows=20)