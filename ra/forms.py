from django import forms
from ra.models import RAAppointment, Account, Project, HIRING_CATEGORY_DISABLED, RAAppointmentAttachment, Program
from ra.models import RARequest, RARequestAttachment
from ra.models import DUTIES_CHOICES_EX, DUTIES_CHOICES_DC, DUTIES_CHOICES_PD, DUTIES_CHOICES_IM, DUTIES_CHOICES_EQ
from ra.models import DUTIES_CHOICES_SU, DUTIES_CHOICES_WR, DUTIES_CHOICES_PM
from ra.models import STUDENT_TYPE, GRAS_PAYMENT_METHOD_CHOICES, RA_PAYMENT_METHOD_CHOICES, NC_PAYMENT_METHOD_CHOICES, RA_BENEFITS_CHOICES, BOOL_CHOICES
from django.core.exceptions import ValidationError
from coredata.models import Person, Semester, Unit
from coredata.forms import PersonField
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text

APPOINTMENT_TYPE = (
    ('AP', 'Appointment/Re-Appointment'),
    ('EX', 'Extension'),
    ('EE', 'Early End'),
    ('FC', 'Funding Change Only'),
    ('CO', 'Correction/Update'),
    ('LS', 'Lump Sum')
)

SCIENCE_ALIVE_TYPE = (
    ('TL', 'Team Lead'),
    ('TE', 'Tech Ed'),
    ('DCRS', 'DCRS Instructor'),
    ('SA', 'Summer Academy Instructor')
)

# TODO: Settings - would really like all of the following to be editable by funding admins (or even sys admins)
# it should be the same across all units, and doesn't change with the semester
# model with a single entry doesn't seem quite right? django-dbsettings?
MIN_WAGE = 15.20
MIN_WEEKS_VACATION = 2
MIN_VACATION_PAY_PERCENTAGE = 4
# unit contacts 
CS_CONTACT = "cs_surrey_assistant@sfu.ca"
MSE_CONTACT = "msedsec@sfu.ca"
ENSC_CONTACT = "enscfin@sfu.ca"
SEE_CONTACT = "fas_admin_manager@sfu.ca"
DEANS_CONTACT = "mrahinsk@sfu.ca"
# general ra contact
FAS_CONTACT = "fasra@sfu.ca"
# intro contacts
URA_CONTACT = "fas_academic_relations@sfu.ca"
PD_CONTACT = "fas_postdoc_support@sfu.ca"


class RARequestIntroForm(forms.ModelForm):
    person = PersonField(label='Appointee', required=False, help_text="Please ensure you are appointing the correct student.")
    supervisor = PersonField(label='Hiring Supervisor', required=True)

    position = forms.CharField(required=False, label="Position Title")
    
    people_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}), label="Any comments about the Appointee or Hiring Supervisor?")

    student = forms.ChoiceField(required=True, choices=STUDENT_TYPE, widget=forms.RadioSelect, label="Is the appointee a student?")
    coop = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Is the appointee a co-op student?")
    mitacs = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Is the appointee's co-op funded by a Mitacs scholarship in their own name?")
    research = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Will the work performed primarily involve research?")
    thesis = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Is the appointment for the student's thesis/project?")

    class Meta:
        model = RARequest
        fields = ('nonstudent', 'first_name', 'last_name', 'email_address', 'person', 'unit', 'hiring_category',)
        labels = {
            'first_name': "Appointee First Name",
            'last_name': "Appointee Last Name",
            'email_address': "Appointee Email Address",
            'nonstudent': "Select if appointee does not have an ID",
            'unit': "Hiring Supervisor's Unit/School",
        }

        widgets = {
            'hiring_category': forms.HiddenInput(),     
        }


    def __init__(self, *args, **kwargs):
        super(RARequestIntroForm, self).__init__(*args, **kwargs)
        
        config_init = ['people_comments', 'coop', 'mitacs', 'student', 'thesis', 'research', 'position']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RARequestIntroForm, self).is_valid(*args, **kwargs)

    # TODO: Make sure total pay and hiring category are calculated properly. Javascript only for now.
    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['people_comments', 'coop', 'mitacs', 'student', 'thesis', 'research', 'position']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])
        
        # add error messages
        nonstudent = cleaned_data.get('nonstudent')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email_address = cleaned_data.get('email_address')
        person = cleaned_data.get('person')

        if nonstudent:
            error_message = 'If the appointee does not have an SFU ID then you must answer this question.'       
            if first_name == None:
                self.add_error('first_name', error_message)
            if last_name == None:
                self.add_error('last_name', error_message)
            if email_address == None:
                self.add_error('email_address', error_message)
        else:
            if person == None:
                self.add_error('person', 'You must provide an SFU ID. If the appointee does not have an SFU ID, please select the checkbox below.')

        if nonstudent == None and person == None:
            raise forms.ValidationError("Cannot be a student and not have an SFU ID.")

        student = cleaned_data.get('student')
        coop = cleaned_data.get('coop')
        mitacs = cleaned_data.get('mitacs')
        research = cleaned_data.get('research')
        thesis = cleaned_data.get('thesis')
        error_message = 'You must answer this question.'
        if (student == 'N'):
            if research == None or research == '':
                self.add_error('research', error_message)
        if (student == 'U' or student == 'M' or student == 'P'):
            if coop == None or coop == '':
                self.add_error('coop', error_message)
            if mitacs == None or mitacs == '':
                self.add_error('mitacs', error_message)
            if mitacs == 'False':
                if research == None or research == '':
                    self.add_error('research', error_message)
                if research == 'True':
                    if thesis == None or thesis == '':
                        self.add_error('thesis', error_message)

        # remove irrelevant information
        if nonstudent:
            self.cleaned_data['person'] = None
        else:
            self.cleaned_data['first_name'] = ''
            self.cleaned_data['last_name'] = ''
            self.cleaned_data['email_address'] = ''
        if (student=='N'):
            self.cleaned_data['coop'] = False
            self.cleaned_data['mitacs'] = False
            self.cleaned_data['thesis'] = False
        elif (student == 'U' or student == 'M' or student == 'P'):
            if (mitacs=='True'):
                self.cleaned_data['research'] = False
                self.cleaned_data['thesis'] = False
            elif (research=='False'):
                self.cleaned_data['thesis'] = False

class RARequestDatesForm(forms.ModelForm):
    backdated = forms.BooleanField(required=False, label="Is this a backdated appointment?")
    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = RARequest
        fields = ('start_date', 'end_date', 'backdated')
        labels = {
            'start_date': "Date Appointment Begins",
            'end_date': "Date Appointment Ends",
        }

    def __init__(self, edit=False, *args, **kwargs):
        super(RARequestDatesForm, self).__init__(*args, **kwargs)
        if not edit:
            self.fields['backdated'].widget=forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if end_date < start_date:
            error_message = "Start date must be before end date."
            self.add_error('end_date', error_message)
            self.add_error('start_date', error_message)

class RARequestFundingSourceForm(forms.ModelForm):
    fs1_unit = forms.IntegerField(required=True, label="Department #1", help_text="CS = 2110; ENSC = 2130; MSE = 2140; SEE = 2150; Dean's Office = 2010, 2020 or 2030")
    fs1_fund = forms.IntegerField(required=True, label="Fund #1", help_text="Example: 11, 13, 21, 31")
    fs1_project = forms.CharField(required=False, label="Project #1", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs1_percentage = forms.DecimalField(required=False, label="Percentage of Funding Source #1 to Total Funding", help_text="Percentages of all funding sources must add up to 100.")
    fs1_start_date = forms.DateField(required=False, label="Start Date #1", help_text="Start Date for Funding Source 1")
    fs1_end_date = forms.DateField(required=False,  label="End Date #1", help_text="End Date for Funding Source 1")

    fs2_option = forms.BooleanField(required=False, label="Please select the following if there is an additional funding source")
    fs2_unit = forms.IntegerField(required=False, label="Department #2", help_text="CS = 2110; ENSC = 2130; MSE = 2140; SEE = 2150; Dean's Office = 2010, 2020 or 2030")
    fs2_fund = forms.IntegerField(required=False, label="Fund #2", help_text="Example: 11, 13, 21, 31")
    fs2_project = forms.CharField(required=False, label="Project #2", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs2_percentage = forms.DecimalField(required=False, label="Percentage of Funding Source #2 to Total Funding", help_text="Percentages of all funding sources must add up to 100.")
    fs2_start_date = forms.DateField(required=False, label="Start Date #2", help_text="Start Date for Funding Source 2")
    fs2_end_date = forms.DateField(required=False,  label="End Date #2", help_text="End Date for Funding Source 2")

    fs3_option = forms.BooleanField(required=False, label="Please select the following if there is an additional funding source")
    fs3_unit = forms.IntegerField(required=False, label="Department #3", help_text="CS = 2110; ENSC = 2130; MSE = 2140; SEE = 2150; Dean's Office = 2010, 2020 or 2030")
    fs3_fund = forms.IntegerField(required=False, label="Fund #3", help_text="Example: 11, 13, 21, 31")
    fs3_project = forms.CharField(required=False, label="Project #3", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs3_percentage = forms.DecimalField(required=False, label="Percentage of Funding Source #3 to Total Funding", help_text="Percentages of all funding sources must add up to 100.")
    fs3_start_date = forms.DateField(required=False, label="Start Date #3", help_text="Start Date for Funding Source 3")
    fs3_end_date = forms.DateField(required=False,  label="End Date #3", help_text="End Date for Funding Source 3")

    class Meta:
        model = RARequest
        fields = ('fs1_unit', 'fs2_unit', 'fs3_unit', 'fs1_fund', 'fs2_fund', 'fs3_fund',
                  'fs1_project', 'fs2_project', 'fs3_project')

    def __init__(self, *args, **kwargs):
        super(RARequestFundingSourceForm, self).__init__(*args, **kwargs)
        config_init = ['fs1_percentage','fs2_percentage','fs3_percentage','fs2_option','fs3_option']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super(RARequestFundingSourceForm, self).clean()
  
        config_clean = ['fs1_percentage','fs2_option', 'fs2_percentage','fs3_option', 
                        'fs3_percentage']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        # for fund 11s, do not require fund
        project_exception_fund = 11

        fs1_fund = cleaned_data.get('fs1_fund')
        fs1_project = cleaned_data.get('fs1_project')

        if fs1_fund != project_exception_fund and (fs1_project == None or fs1_project == ''):
            self.add_error('fs1_project', 'You must answer this question.')

        # add error messages
        start_date = self.initial['start_date']
        end_date = self.initial['end_date']
        fs2_option = cleaned_data.get('fs2_option')
        fs2_unit = cleaned_data.get('fs2_unit')
        fs2_fund = cleaned_data.get('fs2_fund')
        fs2_project = cleaned_data.get('fs2_project')
        fs1_start_date = cleaned_data.get('fs1_start_date')
        fs1_end_date = cleaned_data.get('fs1_end_date')
        fs2_start_date = cleaned_data.get('fs2_start_date')
        fs2_end_date = cleaned_data.get('fs2_end_date')
        fs1_percentage = cleaned_data.get('fs1_percentage')
        fs2_percentage = cleaned_data.get('fs2_percentage')
        fs3_percentage = cleaned_data.get('fs3_percentage')

        if fs2_option:
            error_message = 'If you have a second funding source then you must answer this question.'
            if fs2_unit == None or fs2_unit == '':
                self.add_error('fs2_unit', error_message)
            if fs2_fund == None or fs2_fund == '':
                self.add_error('fs2_fund', error_message)
            if fs2_project == None or fs2_project == '':
                if fs2_fund != project_exception_fund:
                    self.add_error('fs2_project', error_message)
            if fs1_start_date == None or fs1_start_date == '':
                self.add_error('fs1_start_date', error_message)
            if fs1_end_date == None or fs1_end_date == '':
                self.add_error('fs1_end_date', error_message)
            if fs2_start_date == None or fs2_start_date == '':
                self.add_error('fs2_start_date', error_message)
            if fs2_end_date == None or fs2_end_date == '':
                self.add_error('fs2_end_date', error_message)
            if fs1_percentage == None or fs1_percentage == '':
                self.add_error('fs1_percentage', error_message)
            if fs2_percentage == None or fs2_percentage == '':
                self.add_error('fs2_percentage', error_message)

        fs3_option = cleaned_data.get('fs3_option')
        fs3_unit = cleaned_data.get('fs3_unit')
        fs3_fund = cleaned_data.get('fs3_fund')
        fs3_project = cleaned_data.get('fs3_project')
        fs3_start_date = cleaned_data.get('fs3_start_date')
        fs3_end_date = cleaned_data.get('fs3_end_date')

        if fs3_option:
            error_message = 'If you have a third funding source then you must answer this question.'
            if fs3_unit == None or fs3_unit == '':
                self.add_error('fs3_unit', error_message)
            if fs3_fund == None or fs3_fund == '':
                self.add_error('fs3_fund', error_message)
            if fs3_project == None or fs3_project == '':
                if fs3_fund != project_exception_fund:
                    self.add_error('fs3_project', error_message)
            if fs3_start_date == None or fs3_start_date == '':
                self.add_error('fs3_start_date', error_message)
            if fs3_end_date == None or fs3_end_date == '':
                self.add_error('fs3_end_date', error_message)
            if fs3_percentage == None or fs3_percentage == '':
                self.add_error('fs3_percentage', error_message)

        error_message = "Combined Percentages of all Funding Sources Must Add Up to 100%"
        if fs2_option and not fs3_option:
            if fs1_percentage and fs2_percentage:
                percent_sum = fs1_percentage + fs2_percentage
                if percent_sum != 100:
                    self.add_error('fs1_percentage', error_message)
                    self.add_error('fs2_percentage', error_message)
        if fs2_option and fs3_option:
            if fs1_percentage and fs2_percentage and fs3_percentage:
                percent_sum = fs1_percentage + fs2_percentage + fs3_percentage
                if percent_sum != 100:
                    self.add_error('fs1_percentage', error_message)
                    self.add_error('fs2_percentage', error_message)
                    self.add_error('fs3_percentage', error_message)
        
        fs1_start_date = cleaned_data.get('fs1_start_date')
        fs2_start_date = cleaned_data.get('fs2_start_date')
        fs3_start_date = cleaned_data.get('fs3_start_date')

        error_message = "Please ensure at least one funding source start date matches up with the appointment start date."
        if fs2_option and not fs3_option:
            if fs1_start_date and fs2_start_date:
                if (start_date != fs1_start_date) and (start_date != fs2_start_date):
                    self.add_error('fs1_start_date', error_message)
                    self.add_error('fs2_start_date', error_message)
        if fs2_option and fs3_option:
            if fs1_start_date and fs2_start_date and fs3_start_date:
                if (start_date != fs1_start_date) and (start_date != fs2_start_date) and (start_date != fs3_start_date):
                    self.add_error('fs1_start_date', error_message)
                    self.add_error('fs2_start_date', error_message)
                    self.add_error('fs3_start_date', error_message)

        fs1_end_date = cleaned_data.get('fs1_end_date')
        fs2_end_date = cleaned_data.get('fs2_end_date')
        fs3_end_date = cleaned_data.get('fs3_end_date')

        error_message = "Please ensure at least one funding source end date matches up with the appointment end date."
        if fs2_option and not fs3_option:
            if fs1_end_date and fs2_end_date:
                if (end_date != fs1_end_date) and (end_date != fs2_end_date):
                    self.add_error('fs1_end_date', error_message)
                    self.add_error('fs2_end_date', error_message)
        if fs2_option and fs3_option:
            if fs1_end_date and fs2_end_date and fs3_end_date:
                if (end_date != fs1_end_date) and (end_date != fs2_end_date) and (end_date != fs3_end_date):
                    self.add_error('fs1_end_date', error_message)
                    self.add_error('fs2_end_date', error_message)
                    self.add_error('fs3_end_date', error_message)

        error_message = "This date is after the appointment end date."
        if fs2_option:
            if fs1_end_date:
                if fs1_end_date > end_date:
                    self.add_error('fs1_end_date', error_message)
            if fs2_end_date:
                if fs2_end_date > end_date:
                    self.add_error('fs2_end_date', error_message)
        if fs2_option and fs3_option:
            if fs3_end_date:
                if fs3_end_date > end_date:
                    self.add_error('fs3_end_date', error_message)

        error_message = "This date is before the appointment start date."
        if fs2_option:
            if fs1_start_date:
                if fs1_start_date < start_date:
                    self.add_error('fs1_start_date', error_message)
            if fs2_start_date:
                if fs2_start_date < start_date:
                        self.add_error('fs2_start_date', error_message)
        if fs2_option and fs3_option:
            if fs3_start_date:
                if fs3_start_date < start_date:
                    self.add_error('fs3_start_date', error_message)

        error_message = "Ensure start date is before end date."
        if fs2_option:
            if fs1_start_date and fs1_end_date:
                if fs1_start_date > fs1_end_date:
                    self.add_error('fs1_start_date', error_message)
            if fs2_start_date and fs2_end_date:
                if fs2_start_date > fs2_end_date:
                    self.add_error('fs2_start_date', error_message)
        if fs2_option and fs3_option:
            if fs3_start_date and fs3_end_date:
                if fs3_start_date > fs3_end_date:
                    self.add_error('fs3_start_date', error_message)
        
        error_message = "Funding source percentages should be greater than 0."
        if fs2_option:
            if fs1_percentage == 0:
                self.add_error('fs1_percentage', error_message)          
            if fs2_percentage == 0:
                self.add_error('fs2_percentage', error_message)
        if fs3_option:
            if fs3_percentage == 0:
                self.add_error('fs3_percentage', error_message)
        
        start_date = cleaned_data.get('start_date')
        fs1_start_date = cleaned_data.get('fs1_start_date')
        fs2_start_date = cleaned_data.get('fs2_start_date')
        fs3_start_date = cleaned_data.get('fs3_start_date')

        # remove irrelevant information
        if not fs3_option: 
            self.cleaned_data['fs3_unit'] = 0
            self.cleaned_data['fs3_fund'] = 0
            self.cleaned_data['fs3_project'] = ''
            self.cleaned_data['fs3_percentage'] = 0
            self.cleaned_data['fs3_start_date'] = ''
            self.cleaned_data['fs3_end_date'] = ''

        if not fs2_option:
            self.cleaned_data['fs1_start_date'] = ''
            self.cleaned_data['fs1_end_date'] = ''

            self.cleaned_data['fs2_unit'] = 0
            self.cleaned_data['fs2_fund'] = 0
            self.cleaned_data['fs2_project'] = ''
            self.cleaned_data['fs2_percentage'] = 0
            self.cleaned_data['fs2_start_date'] = ''
            self.cleaned_data['fs2_end_date'] = ''

class RARequestGraduateResearchAssistantForm(forms.ModelForm):
    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)

    # fill out if backdated
    backdated = forms.BooleanField(required=False, widget=forms.HiddenInput)
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum")
    backdate_hours = forms.DecimalField(required=False, label="How many hours is this lump sum based on?")
    backdate_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':15}), label="Please provide the reason for this backdated appointment")
    
    gras_payment_method = forms.ChoiceField(required=False,
                                            choices=GRAS_PAYMENT_METHOD_CHOICES, 
                                            widget=forms.RadioSelect, 
                                            label="Scholarship (No added benefit & vacation cost)",
                                            help_text='Canadian bank status impacts how students will be paid. This generally applies to International ' +
                                            'students currently working outside of Canada, who do not have banking status in Canada. If the status is ' + 
                                            'unknown please confirm with the student.')
    total_gross = forms.DecimalField(required=False, label="Total Gross Salary Paid", max_digits=8, decimal_places=2)
    biweekly_hours = forms.DecimalField(required=False, label="Bi-Weekly Hours", max_digits=8, decimal_places=1)
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    gross_hourly = forms.DecimalField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = RARequest
        fields = ('gras_payment_method', 'total_pay', 'total_gross', 'biweekly_hours', 'biweekly_salary', 'gross_hourly')
        widgets = {
            'total_pay': forms.HiddenInput(),     
        }
    
    def __init__(self, *args, **kwargs):
        super(RARequestGraduateResearchAssistantForm, self).__init__(*args, **kwargs)
        
        config_init = ['backdate_lump_sum', 'backdate_hours', 'backdate_reason']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['backdate_lump_sum', 'backdate_hours', 'backdate_reason']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])
        
        # add error messages
        error_message = "You must answer this question."

        gras_payment_method = cleaned_data.get('gras_payment_method')
        total_gross = cleaned_data.get('total_gross')
        gross_hourly = cleaned_data.get('gross_hourly')
        biweekly_hours = cleaned_data.get('biweekly_hours')
        biweekly_salary = cleaned_data.get('biweekly_salary')
        
        backdated = self.initial["backdated"]
        backdate_lump_sum = cleaned_data.get('backdate_lump_sum')
        backdate_hours = cleaned_data.get('backdate_hours')
        backdate_reason = cleaned_data.get('backdate_reason')

        if backdated:
            if backdate_lump_sum == 0 or backdate_lump_sum == None or backdate_lump_sum == '':
                self.add_error('backdate_lump_sum', error_message)          
            if backdate_hours == 0 or backdate_hours == None or backdate_hours == '':
                self.add_error('backdate_hours', error_message)
            if backdate_reason == '' or backdate_reason == None:
                self.add_error('backdate_reason', error_message)
        elif gras_payment_method == None or gras_payment_method == "":
            self.add_error('gras_payment_method', error_message)
        else:
            if gras_payment_method == "LS" or gras_payment_method == "LE":
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
            if gras_payment_method == "BW":
                if gross_hourly < MIN_WAGE:
                    raise forms.ValidationError('Gross Hourly Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % MIN_WAGE) + ')')
                if biweekly_hours == 0 or biweekly_hours == None:
                    self.add_error('biweekly_hours', error_message)
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
        
        # remove irrelevant information
        if backdated:
            self.cleaned_data['gras_payment_method'] = ''
            self.cleaned_data['total_gross'] = 0
            self.cleaned_data['biweekly_hours'] = 0
            self.cleaned_data['biweekly_salary'] = 0
            self.cleaned_data['gross_hourly'] = 0
        else: 
            self.cleaned_data["backdate_lump_sum"] = 0
            self.cleaned_data["backdate_hours"] = 0
            self.cleaned_data["backdate_reason"] = ''
            if gras_payment_method == "LS" or gras_payment_method == "LE":
                self.cleaned_data['biweekly_hours'] = 0
                self.cleaned_data['biweekly_salary'] = 0
                self.cleaned_data['gross_hourly'] = 0
                


class RARequestNonContinuingForm(forms.ModelForm):
    # Form for NonContinuing Appointees
    # BiWeekly Payment Method -> total_gross, weeks_vacation, biweekly_hours, should also calculate biweekly_salary, gross_hourly and vacation_hours
    # Hourly Payment Method -> gross_hourly, vacation_pay, biweekly_hours

    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)
    
    # fill out if backdated
    backdated = forms.BooleanField(required=False, widget=forms.HiddenInput)
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum")
    backdate_hours = forms.DecimalField(required=False, label="How many hours is this lump sum based on?")
    backdate_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':15}), label="Please provide the reason for this backdated appointment")

    nc_duties = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':15}), label="Duties", help_text="Please enter duties in a comma-separated list.")
    
    nc_payment_method = forms.ChoiceField(required=False, choices=RA_PAYMENT_METHOD_CHOICES, widget=forms.RadioSelect, label="Please select from the following")
    
    total_gross = forms.DecimalField(required=False, label="Total Gross Salary Paid", max_digits=8, decimal_places=2)
    weeks_vacation = forms.DecimalField(required=False, label="Weeks Vacation (Minimum 2)", max_digits=8, decimal_places=1)
    biweekly_hours = forms.DecimalField(required=False, label="Bi-Weekly Hours", max_digits=8, decimal_places=1)
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    vacation_hours = forms.DecimalField(required=False, widget=forms.HiddenInput)
    gross_hourly = forms.DecimalField(required=False, label="Gross Hourly", max_digits=8, decimal_places=2)
    vacation_pay = forms.DecimalField(required=False, label="Vacation Pay % (Minimum 4%)", max_digits=8, decimal_places=1)

    class Meta:
        model = RARequest
        fields = ('nc_payment_method', 'total_pay', 'backdated', 'total_gross','weeks_vacation','biweekly_hours',
                  'biweekly_salary','vacation_hours','gross_hourly','vacation_pay')

        widgets = {
            'total_pay': forms.HiddenInput(),     
        }

    def __init__(self, *args, **kwargs):
        super(RARequestNonContinuingForm, self).__init__(*args, **kwargs) 
        
        config_init = ['nc_duties', 'backdate_lump_sum', 'backdate_hours', 'backdate_reason']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['nc_duties', 'backdate_lump_sum', 'backdate_hours', 'backdate_reason']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        error_message = "You must answer this question."

        nc_payment_method = cleaned_data.get('nc_payment_method')
        total_gross = cleaned_data.get('total_gross')
        weeks_vacation = cleaned_data.get('weeks_vacation')
        biweekly_salary = cleaned_data.get('biweekly_salary')
        gross_hourly = cleaned_data.get('gross_hourly')
        biweekly_hours = cleaned_data.get('biweekly_hours')
        vacation_hours = cleaned_data.get('vacation_hours')

        gross_hourly = cleaned_data.get('gross_hourly')
        vacation_pay = cleaned_data.get('vacation_pay')
        biweekly_hours = cleaned_data.get('biweekly_hours')
        
        backdated = self.initial["backdated"]
        backdate_lump_sum = cleaned_data.get('backdate_lump_sum')
        backdate_hours = cleaned_data.get('backdate_hours')
        backdate_reason = cleaned_data.get('backdate_reason')

        if backdated:
            if backdate_lump_sum == 0 or backdate_lump_sum == None or backdate_lump_sum == '':
                self.add_error('backdate_lump_sum', error_message)          
            if backdate_hours == 0 or backdate_hours == None or backdate_hours == '':
                self.add_error('backdate_hours', error_message)
            if backdate_reason == '' or backdate_reason == None:
                self.add_error('backdate_reason', error_message)
        elif nc_payment_method == None or nc_payment_method == "":
            self.add_error('nc_payment_method', error_message)
        else:
            if nc_payment_method == "BW":
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
                if weeks_vacation == None:
                    self.add_error('weeks_vacation', error_message)
                elif weeks_vacation < MIN_WEEKS_VACATION:
                    self.add_error('weeks_vacation', ('Weeks Vacation Must Be At Least ' + str(MIN_WEEKS_VACATION) + ' Weeks'))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)
                if gross_hourly < MIN_WAGE:
                    raise forms.ValidationError('Gross Hourly Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % MIN_WAGE) + ')')
            if nc_payment_method == "H":
                if gross_hourly == None:
                    self.add_error('gross_hourly', error_message)
                elif gross_hourly < MIN_WAGE:
                    self.add_error('gross_hourly', ('Gross Hourly Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % MIN_WAGE) + ')'))
                if vacation_pay == None:
                    self.add_error('vacation_pay', error_message)
                elif vacation_pay < MIN_VACATION_PAY_PERCENTAGE:
                    self.add_error('vacation_pay', ('Vacation Pay Must Be At Least % ' + str(MIN_VACATION_PAY_PERCENTAGE)))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)

        # remove irrelevant fields
        if backdated:
            self.cleaned_data["nc_payment_method"] = ''
            self.cleaned_data["total_gross"] = 0
            self.cleaned_data["weeks_vacation"] = 0
            self.cleaned_data["biweekly_salary"] = 0
            self.cleaned_data["gross_hourly"] = 0
            self.cleaned_data["vacation_hours"] = 0
            self.cleaned_data["vacation_pay"] = 0
            self.cleaned_data["biweekly_hours"] = 0
        else: 
            self.cleaned_data["backdate_lump_sum"] = 0
            self.cleaned_data["backdate_hours"] = 0
            self.cleaned_data["backdate_reason"] = ''
            if nc_payment_method == "H":
                self.cleaned_data["total_gross"] = 0
                self.cleaned_data["weeks_vacation"] = 0
                self.cleaned_data["biweekly_salary"] = 0
                self.cleaned_data["vacation_hours"] = 0
            elif nc_payment_method == "BW":
                self.cleaned_data["vacation_pay"] = 0

class RARequestResearchAssistantForm(forms.ModelForm):
    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)
    # fill out if backdated
    backdated = forms.BooleanField(required=False, widget=forms.HiddenInput)
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum")
    backdate_hours = forms.DecimalField(required=False, label="How many hours is this lump sum based on?")
    backdate_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':15}), label="Please provide the reason for this backdated appointment")
    
    ra_payment_method = forms.ChoiceField(required=False, choices=RA_PAYMENT_METHOD_CHOICES, widget=forms.RadioSelect, label="Please select from the following")
    
    total_gross = forms.DecimalField(required=False, label="Total Gross Salary Paid", max_digits=8, decimal_places=2)
    weeks_vacation = forms.DecimalField(required=False, label="Weeks Vacation (Minimum 2)", max_digits=8, decimal_places=1)
    biweekly_hours = forms.DecimalField(required=False, label="Bi-Weekly Hours", max_digits=8, decimal_places=1)
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    vacation_hours = forms.DecimalField(required=False, widget=forms.HiddenInput)
    gross_hourly = forms.DecimalField(required=False, label="Gross Hourly", max_digits=8, decimal_places=2)
    vacation_pay = forms.DecimalField(required=False, label="Vacation Pay % (Minimum 4%)", max_digits=8, decimal_places=1)
    
    ra_benefits = forms.ChoiceField(required=True, choices=RA_BENEFITS_CHOICES, widget=forms.RadioSelect, 
                                    label='Are you willing to provide extended health benefits?', 
                                    help_text=mark_safe('<a href="http://www.sfu.ca/human-resources/research.html">Please click here and refer to "Summary of RA Benefit Plan" for the cost of each medical and dental care plan</a>'))

    ra_duties_ex = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_EX, widget=forms.CheckboxSelectMultiple,
                                             label="Experimental/Research Activities")
    ra_duties_dc = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_DC, widget=forms.CheckboxSelectMultiple,
                                             label="Data Collection/Analysis")
    ra_duties_pd = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_PD, widget=forms.CheckboxSelectMultiple,
                                             label="Project Development")
    ra_duties_im = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_IM, widget=forms.CheckboxSelectMultiple,
                                             label="Information Management")
    ra_duties_eq = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_EQ, widget=forms.CheckboxSelectMultiple,
                                             label="Equipment/Inventory Management and Development")
    ra_duties_su = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_SU, widget=forms.CheckboxSelectMultiple,
                                             label="Supervision")
    ra_duties_wr = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_WR, widget=forms.CheckboxSelectMultiple,
                                             label="Writing/Reporting")
    ra_duties_pm = forms.MultipleChoiceField(required=False, choices=DUTIES_CHOICES_PM, widget=forms.CheckboxSelectMultiple,
                                             label="Project Management")    
    ra_other_duties = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}), label="Other RA Duties")

    class Meta:
        model = RARequest
        fields = ('ra_payment_method', 'total_pay', 'backdated', 'total_gross','weeks_vacation','biweekly_hours',
                  'biweekly_salary','vacation_hours','gross_hourly','vacation_pay')

        widgets = {
            'total_pay': forms.HiddenInput() 
        }

    def __init__(self, *args, **kwargs):
        super(RARequestResearchAssistantForm, self).__init__(*args, **kwargs)
        
        config_init = ['ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 
                'ra_duties_eq', 'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 
                'ra_benefits', 'ra_other_duties', 'backdate_lump_sum', 'backdate_hours', 'backdate_reason']
        
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['ra_payment_method', 'ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 
                'ra_duties_eq', 'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 'ra_benefits', 'ra_other_duties', 
                'backdate_lump_sum', 'backdate_hours', 'backdate_reason']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        error_message = "You must answer this question."

        ra_payment_method = cleaned_data.get('ra_payment_method')
        total_gross = cleaned_data.get('total_gross')
        weeks_vacation = cleaned_data.get('weeks_vacation')
        biweekly_salary = cleaned_data.get('biweekly_salary')
        gross_hourly = cleaned_data.get('gross_hourly')
        biweekly_hours = cleaned_data.get('biweekly_hours')
        vacation_hours = cleaned_data.get('vacation_hours')
        vacation_pay = cleaned_data.get('vacation_pay')
        
        backdated = cleaned_data.get('backdated')
        backdate_lump_sum = cleaned_data.get('backdate_lump_sum')
        backdate_hours = cleaned_data.get('backdate_hours')
        backdate_reason = cleaned_data.get('backdate_reason')

        if backdated:
            if backdate_lump_sum == 0 or backdate_lump_sum == None or backdate_lump_sum == '':
                self.add_error('backdate_lump_sum', error_message)          
            if backdate_hours == 0 or backdate_hours == None or backdate_hours == '':
                self.add_error('backdate_hours', error_message)
            if backdate_reason == '' or backdate_reason == None:
                self.add_error('backdate_reason', error_message)
        elif ra_payment_method == None or ra_payment_method == "":
            self.add_error('ra_payment_method', error_message)
        else:
            if ra_payment_method == "BW":
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
                if weeks_vacation == None:
                    self.add_error('weeks_vacation', error_message)
                elif weeks_vacation < MIN_WEEKS_VACATION:
                    self.add_error('weeks_vacation', ('Weeks Vacation Must Be At Least ' + str(MIN_WEEKS_VACATION) + ' Weeks'))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)
                if gross_hourly < MIN_WAGE:
                    raise forms.ValidationError('Gross Hourly Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % MIN_WAGE) + ')')
            elif ra_payment_method == "H":
                if gross_hourly == None:
                    self.add_error('gross_hourly', error_message)
                elif gross_hourly < MIN_WAGE:
                    self.add_error('gross_hourly', ('Gross Hourly Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % MIN_WAGE) + ')'))
                if vacation_pay == None:
                    self.add_error('vacation_pay', error_message)
                elif vacation_pay < MIN_VACATION_PAY_PERCENTAGE:
                    self.add_error('vacation_pay', ('Vacation Pay Must Be At Least % ' + str(MIN_VACATION_PAY_PERCENTAGE)))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)
        
        # remove irrelevant fields
        if backdated:
            self.cleaned_data["ra_payment_method"] = ''
            self.cleaned_data["total_gross"] = 0
            self.cleaned_data["weeks_vacation"] = 0
            self.cleaned_data["biweekly_hours"] = 0
            self.cleaned_data["biweekly_salary"] = 0
            self.cleaned_data["vacation_hours"] = 0
            self.cleaned_data["gross_hourly"] = 0
            self.cleaned_data["vacation_pay"] = 0
        else: 
            self.cleaned_data["backdate_lump_sum"] = 0
            self.cleaned_data["backdate_hours"] = 0
            self.cleaned_data["backdate_reason"] = ''
            if ra_payment_method == "H":
                self.cleaned_data["total_gross"] = 0
                self.cleaned_data["weeks_vacation"] = 0
                self.cleaned_data["biweekly_salary"] = 0
                self.cleaned_data["vacation_hours"] = 0
            elif ra_payment_method == "BW":
                self.cleaned_data["vacation_pay"] = 0
            
class RARequestSupportingForm(forms.ModelForm):
    funding_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}), label="Any comments about funding?")
    
    class Meta:
        model = RARequest
        fields = ('file_attachment_1', 'file_attachment_2',)
        labels = {'file_attachment_1': "Supplementary Document #1",
                  'file_attachment_2': "Supplementary Document #2",
        }
        
        help_texts = {
                    'file_attachment_1': "Both of these fields are optional.",
                    'file_attachment_2': "If co-op appointment, please upload co-op forms.",
        }

    def __init__(self, *args, **kwargs):
        super(RARequestSupportingForm, self).__init__(*args, **kwargs)  
        
        config_init = ['funding_comments']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

class RARequestNoteForm(forms.ModelForm):
    admin_notes = forms.CharField(required=False, label="Administrative Notes", widget=forms.Textarea)

    class Meta:
        model = RARequest
        fields = ()

    def __init__(self, *args, **kwargs):
        super(RARequestNoteForm, self).__init__(*args, **kwargs)
        config_init = ['admin_notes']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['admin_notes']
        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

class RARequestAdminForm(forms.ModelForm):
    funding_available = forms.BooleanField(required=False, label="")
    grant_active = forms.BooleanField(required=False, label="")
    salary_allowable = forms.BooleanField(required=False, label="")
    supervisor_check = forms.BooleanField(required=False, label="")
    visa_valid = forms.BooleanField(required=False, label="")
    payroll_collected = forms.BooleanField(required=False, label="")
    paf_signed = forms.BooleanField(required=False, label="")

    class Meta:
        model = RARequest
        fields = ()
    
    def __init__(self, *args, **kwargs):
        super(RARequestAdminForm, self).__init__(*args, **kwargs)
        config_init = ['funding_available', 'grant_active', 'salary_allowable', 'supervisor_check', 'visa_valid',
                        'payroll_collected', 'paf_signed']
        
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
    
    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['funding_available', 'grant_active', 'salary_allowable', 'supervisor_check', 'visa_valid',
                        'payroll_collected', 'paf_signed']
        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])
        
class RARequestAdminAttachmentForm (forms.ModelForm):
    class Meta:
        model = RARequestAttachment
        exclude = ('req', 'created_by')

class RARequestPAFForm (forms.Form):
    appointment_type = forms.ChoiceField(required=True, choices=APPOINTMENT_TYPE, widget=forms.RadioSelect, label="Type Of Appointment")

class RARequestLetterForm(forms.ModelForm):
    class Meta:
        model = RARequest
        fields = ('offer_letter_text',)
        widgets = {
                   'offer_letter_text': forms.Textarea(attrs={'rows': 25, 'cols': 70}),
                   }

class RARequestScienceAliveForm(forms.Form):
    letter_type = forms.ChoiceField(required=True, choices=SCIENCE_ALIVE_TYPE, widget=forms.RadioSelect, label="Type Of Science Alive Letter")
    final_bullet = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':6}), help_text="Leave blank if none.", 
                                   label="If you have anything to add in an additional bullet point, please enter here")
    
class RARequestAdminPAFForm(forms.ModelForm):
    position_no = forms.IntegerField(required=False, label="Position #")
    object_code = forms.IntegerField(required=False, label="Object Code for Funding Sources")
    fs1_program = forms.IntegerField(required=False, label="Program for Funding Source #1")
    fs2_program = forms.IntegerField(required=False, label="Program for Funding Source #2")
    fs3_program = forms.IntegerField(required=False, label="Program for Funding Source #3")
    paf_comments = forms.CharField(required=False, max_length=310, widget=forms.Textarea(attrs={'rows':6}), label="Comments", help_text = "Maximum of 310 characters")

    class Meta:
        model = RARequest
        fields = ()

    def __init__(self, *args, **kwargs):
        super(RARequestAdminPAFForm, self).__init__(*args, **kwargs)
        config_init = ['position_no', 'object_code', 'fs1_program', 'fs2_program', 'fs3_program', 'paf_comments']
        
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
    
    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['position_no', 'object_code', 'fs1_program', 'fs2_program', 'fs3_program', 'paf_comments']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])
    

class AppointeeSearchForm(forms.Form):
    appointee = PersonField(required=True, label="Appointee", help_text="Type to search for a student's appointments/requests.")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(AppointeeSearchForm, self).is_valid(*args, **kwargs)

class SupervisorSearchForm(forms.Form):
    supervisor = PersonField(required=True, label="Supervisor", help_text="Type to search for an appointee's appointments/requests.")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(SupervisorSearchForm, self).is_valid(*args, **kwargs)

class RAForm(forms.ModelForm):
    person = PersonField(label='Hire')
    sin = forms.IntegerField(label='SIN', required=False)
    use_hourly = forms.BooleanField(label='Use Hourly Rate', initial=False, required=False,
                                    help_text='Should the hourly rate be displayed on the contract (or total hours for lump sum contracts)?')
    
    class Meta:
        model = RAAppointment
        exclude = ('config','offer_letter_text','deleted')

    def __init__(self, *args, **kwargs):
        super(RAForm, self).__init__(*args, **kwargs)
        choices = self.fields['hiring_category'].choices
        choices = [(k,v) for k,v in choices if k not in HIRING_CATEGORY_DISABLED]
        self.fields['hiring_category'].choices = choices

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RAForm, self).is_valid(*args, **kwargs)

    def clean_sin(self):
        sin = self.cleaned_data['sin']
        try:
            emplid = int(self['person'].value())
        except ValueError:
            raise forms.ValidationError("The correct format for a SIN is XXXXXXXXX, all numbers, no spaces or dashes.")
        people = Person.objects.filter(emplid=emplid)
        if people:
            person = people[0]
            person.set_sin(sin)
            person.save()
        return sin

    def clean_hours(self):
        data = self.cleaned_data['hours']
        if self.cleaned_data['pay_frequency'] == 'L':
            return data

        if int(data) > 168:
            raise forms.ValidationError("There are only 168 hours in a week.")
        if int(data) < 0:
            raise forms.ValidationError("One cannot work negative hours.")
        return data

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data 
  
class RALetterForm(forms.ModelForm):
    class Meta:
        model = RAAppointment
        fields = ('offer_letter_text',)
        widgets = {
                   'offer_letter_text': forms.Textarea(attrs={'rows': 25, 'cols': 70}),
                   }


class LetterSelectForm(forms.Form):
    letter_choice = forms.ChoiceField(label='Select a letter', required=True, help_text='Please select the appropriate letter template for this RA.')

    def __init__(self, choices=[], *args, **kwargs):
        super(LetterSelectForm, self).__init__(*args, **kwargs)
        self.fields["letter_choice"].choices = choices


class StudentSelect(forms.TextInput):
    # widget to input an emplid; presumably with autocomplete in the frontend
    pass


class StudentField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super(StudentField, self).__init__(*args, queryset=Person.objects.none(), widget=StudentSelect(attrs={'size': 20}), help_text="Type to search for a student's appointments.", **kwargs)

    def to_python(self, value):
        try:
            st= Person.objects.get(emplid=value)
        except (ValueError, Person.DoesNotExist):
            raise forms.ValidationError("Unknown person selected")
        return st


class RASearchForm(forms.Form):
    search = StudentField()


class RABrowseForm(forms.Form):
    current = forms.BooleanField(label='Only current appointments', initial=True, help_text='Appointments active now (or within two weeks).')


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        exclude = ('hidden',)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('hidden',)
        widgets = {
            'project_prefix': forms.TextInput(attrs={'size': 1})
        }


class SemesterConfigForm(forms.Form):
    unit = forms.ModelChoiceField(queryset=Unit.objects.all())
    start_date = forms.DateField(required=True, help_text="Default start date for contracts")
    end_date = forms.DateField(required=True, help_text="Default end date for contracts")


class RAAppointmentAttachmentForm(forms.ModelForm):
    class Meta:
        model = RAAppointmentAttachment
        exclude = ('appointment', 'created_by')


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        exclude = ('hidden',)
