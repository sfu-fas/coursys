from django import forms
import datetime
from django.utils.html import format_html
from django.forms import BaseInlineFormSet, inlineformset_factory
from coredata.forms import PersonField
from postdoc.models import PostDoc, PostDocAttachment, PostDocFundingSource, PostDocSupervisor
from postdoc.choices import TYPE_CHOICES, WORK_ELIGIBILITY_STATUS_CHOICES, WORK_HOURS_CHOICES, DEPT_CHOICES, FUND_CHOICES, BOOL_CHOICES

class PostDocForm(forms.ModelForm):
    person = PersonField(label='PDF SFU ID', required=True)
    type = forms.ChoiceField(choices=TYPE_CHOICES, required=True)
    doctorate_completed_date = forms.DateField(label='Date Doctorate Completed', required=True)
    work_eligibility_status = forms.ChoiceField(choices=WORK_ELIGIBILITY_STATUS_CHOICES, required=True, help_text=format_html('<a id="postdoc-visa-link" href="#" style="display:none;"><b>+ Add New Visa</b></a>'))
    relocation_reimbursement = forms.TypedChoiceField(label='Relocation Reimbursement?', choices=BOOL_CHOICES, widget=forms.RadioSelect, required=True, coerce=lambda v: v == 'True', initial=False)
    relocation_reimbursement_amount = forms.DecimalField(label='Relocation Reimbursement Amount', required=False, min_value=0, decimal_places=2)
    involved_teaching = forms.TypedChoiceField(label='Involved teaching during Post Doc appointment?', choices=BOOL_CHOICES, widget=forms.RadioSelect, required=True, coerce=lambda v: v == 'True', initial=False)
    other_info = forms.CharField(label='Other information about the Appointee or Hiring Supervisor', required=False, max_length=500, widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 500}))
    start_date = forms.DateField(required=True, label='Appointment Start Date')
    end_date = forms.DateField(required=True, label='Appointment End Date')
    benefits_estimation = forms.DecimalField(label='Benefits Estimation %', required=True, min_value=0, decimal_places=2)
    work_hours = forms.ChoiceField(choices=WORK_HOURS_CHOICES, required=True)
    hours_of_work = forms.DecimalField(label='Hours of Work Per Week', required=False, min_value=0, decimal_places=2)
    vacation_entitlement_weeks = forms.DecimalField(label='Vacation Entitlement Per Year (in Weeks)', required=True, min_value=0, decimal_places=2)
    has_lump_sum_payment = forms.TypedChoiceField(label='Is this a lump sum payment?', choices=BOOL_CHOICES, widget=forms.RadioSelect, required=True, coerce=lambda v: v == 'True')
    annual_salary_amount = forms.DecimalField(label='Annual Salary Amount', required=False, min_value=0, decimal_places=2)
    lump_sum_payment = forms.DecimalField(label='Lump Sum Payment', required=False, min_value=0, decimal_places=2)

    class Meta:
        model = PostDoc
        fields = ('person', 'unit', 'type', 'doctorate_completed_date', 'work_eligibility_status', 'relocation_reimbursement', 'relocation_reimbursement_amount',
                  'involved_teaching', 'other_info', 'start_date', 'end_date', 'has_lump_sum_payment', 'annual_salary_amount', 'lump_sum_payment',
                  'benefits_estimation', 'work_hours', 'hours_of_work', 'vacation_entitlement_weeks')
        labels = {'unit': 'Hiring Unit/School'}

    def __init__(self, *args, **kwargs):
        units = kwargs.pop('units', None)
        super().__init__(*args, **kwargs)

        if units is not None:
            self.fields['unit'].choices = [(u.id, u.name) for u in units]

        self.initial['has_lump_sum_payment'] = True if self.instance.lump_sum_payment is not None else False

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(PostDocForm, self).is_valid(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('relocation_reimbursement'):
            reimbursement_amount = cleaned_data.get('relocation_reimbursement_amount')
            if reimbursement_amount is None or reimbursement_amount <= 0:
                self.add_error('relocation_reimbursement_amount', 'You must answer this question.')
        else:
            cleaned_data['relocation_reimbursement_amount'] = 0

        if cleaned_data.get('work_hours') == 'PART_TIME':
            hours_of_work = cleaned_data.get('hours_of_work')
            if hours_of_work is None or hours_of_work <= 0:
                self.add_error('hours_of_work', 'You must answer this question.')
        elif cleaned_data.get('work_hours') == 'FULL_TIME':
            cleaned_data['hours_of_work'] = 35
        else:
            cleaned_data['hours_of_work'] = 0

        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date must be on or after the start date.')

        if cleaned_data.get('has_lump_sum_payment'):
            lump_sum = cleaned_data.get('lump_sum_payment')
            if lump_sum is None or lump_sum <= 0:
                self.add_error('lump_sum_payment', 'You must answer this question.')
            cleaned_data['annual_salary_amount'] = None
        else:
            annual_salary = cleaned_data.get('annual_salary_amount')
            if annual_salary is None:
                self.add_error('annual_salary_amount', 'You must answer this question.')
            elif annual_salary <= 0:
                self.add_error('annual_salary_amount', 'Value must be greater than 0.')
            cleaned_data['lump_sum_payment'] = None

        return cleaned_data

class PostDocSupervisorForm(forms.ModelForm):
    supervisor = PersonField(label='Supervisor', required=True)

    class Meta:
        model = PostDocSupervisor
        fields = ('supervisor',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and getattr(self.instance, 'supervisor_id', None):
            sup = self.instance.supervisor
            if sup and sup.emplid:
                self.initial['supervisor'] = sup.emplid

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super().is_valid(*args, **kwargs)


class BasePostDocSupervisorFormSet(BaseInlineFormSet):
    default_error_messages = {
        **BaseInlineFormSet.default_error_messages,
        'too_few_forms': 'Enter at least one supervisor.',
    }

    def clean(self):
        super().clean()
        num_supervisors = 0
        supervisors_seen = set()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue

            supervisor = form.cleaned_data.get('supervisor')
            if not supervisor:
                continue

            num_supervisors += 1
            if supervisor.pk in supervisors_seen:
                form.add_error('supervisor', 'Duplicate supervisor.')
            supervisors_seen.add(supervisor.pk)

        if num_supervisors < 1:
            raise forms.ValidationError('At least one supervisor is required.')


PostDocSupervisorFormSet = inlineformset_factory(PostDoc, PostDocSupervisor, form=PostDocSupervisorForm, formset=BasePostDocSupervisorFormSet, extra=3, can_delete=True, min_num=1, validate_min=True, max_num=3, validate_max=True)

class PostDocFundingSourceForm(forms.ModelForm):
    unit = forms.TypedChoiceField(choices=DEPT_CHOICES, required=True, label='Department')
    fund = forms.TypedChoiceField(choices=FUND_CHOICES, required=True, label='Fund')
    project = forms.CharField(required=False, label='Project')
    amount = forms.DecimalField(required=True, min_value=0, label='Amount')
    start_date = forms.DateField(required=True, label='Start date')
    end_date = forms.DateField(required=True, label='End date')

    class Meta:
        model = PostDocFundingSource
        fields = ('unit', 'fund', 'project', 'amount', 'start_date', 'end_date')

class BasePostDocFundingSourceFormSet(BaseInlineFormSet):
    default_error_messages = {
        **BaseInlineFormSet.default_error_messages,
        'too_few_forms': 'Enter at least one funding source.',
    }

    def clean(self):
        super().clean()
        project_exception_fund = 11
        funding_sources = 0

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue

            if form.cleaned_data.get('DELETE'):
                continue

            unit = form.cleaned_data.get('unit')
            fund = form.cleaned_data.get('fund')
            project = (form.cleaned_data.get('project') or '').strip()
            amount = form.cleaned_data.get('amount')
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

            is_blank = not any((unit, fund, project, amount, start_date, end_date))

            if is_blank:
                continue

            funding_sources += 1
            if fund != project_exception_fund and not project:
                form.add_error('project', 'Required unless fund is 11.')
            if start_date and end_date and end_date < start_date:
                form.add_error('end_date', 'End date must be on or after start date.')

        if funding_sources == 0:
            raise forms.ValidationError('At least one funding source is required.')


PostDocFundingSourceFormSet = inlineformset_factory(PostDoc, PostDocFundingSource, form=PostDocFundingSourceForm, formset=BasePostDocFundingSourceFormSet, extra=3, can_delete=True, min_num=1, validate_min=True, max_num=3, validate_max=True)

class PostDocNoteForm(forms.ModelForm):
    admin_notes = forms.CharField(required=False, label='Administrative Notes', widget=forms.Textarea)

    class Meta:
        model = PostDoc
        fields = ('admin_notes',)

class PostDocAdminAttachmentForm(forms.ModelForm):
    class Meta:
        model = PostDocAttachment
        exclude = ('appt', 'created_by')

class PostDocDownloadForm(forms.Form):
    start_date = forms.DateField(label='Start Date Range (Begins)', widget=forms.DateInput(format='%Y-%m-%d'), input_formats=['%Y-%m-%d'], required=True)
    end_date = forms.DateField(label='Start Date Range (Ends)', help_text='PDFs in download will start within the indicated range.', widget=forms.DateInput(format='%Y-%m-%d'), input_formats=['%Y-%m-%d'], required=True)
    current = forms.ChoiceField(label='Only current PDFs (ignores above date range)', widget=forms.RadioSelect, choices=BOOL_CHOICES, initial='False', help_text='PDFs active now (or within two weeks).', required=False)
    include_visa_status = forms.ChoiceField(label='Include Visas and Visa Expiries in Result', widget=forms.RadioSelect, choices=BOOL_CHOICES, initial='True', help_text='Include Visa Status', required=False)

    def __init__(self, *args, **kwargs):
        super(PostDocDownloadForm, self).__init__(*args, **kwargs)
        today = datetime.date.today()
        self.initial['start_date'] = today - datetime.timedelta(days=1095)
        self.initial['end_date'] = today
