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
import os, datetime

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

FUND_CHOICES = (
    ('', '-----------'), (11, '11'), (13, '13'), (21, '21'), (23, '23'), (25, '25'), (29, '29'), (31, '31'), (32, '32'), (35, '35'), (36, '36'), (37, '37'), (38, '38'), (40, '40')
)

DEPT_CHOICES = (
    ('', '-----------'), (2110, '2110 (CMPT)'), (2130, '2130 (ENSC)'), (2140, '2140 (MSE)'), (2150, '2150 (SEE)'), (2020, "2020 (Dean's Office)"), (2030, "2030 (Dean's Office)")
)

PROGRAM_CHOICES = (
    ('', '-----------'), (00000, '00000 - None'), (90140, '90140 - Research Support'), (20015, '20015 - FAS Outreach Programming'), (90010, '90010 - Communication and Marketing')
)

OBJECT_CHOICES = (
    ('', '-----------'), (5164, '5164 - University Research Associate'), (5372, '5372 - Hourly Staff - Student'), (5378, '5378 - Salaried Staff-Students'), (5412, '5412 - Salaries Research Scientists'),
    (5414, '5414 - Salaries Visiting Scientists'), (5416, '5416 - Salaries Research Assoc'), (5418, '5418 - Salaries Research Technician'), (5430, '5430 - Sals Non-Students RA'), (5432, '5432 - Sals Undergrad RA Cdn'),
    (5434, '5434 - Sals Undergrad RA Foreign'), (5436, '5436 - Sals Masters RA Cdn'), (5438, '5438 - Sals Masters RA Foreign'), (5440, '5440 - Sals Doctorate RA Cdn'), (5442, '5442 - Sals Doctorate RA Foreign'),
    (5444, '5444 - Sals Post-Doc RA Cdn'), (5446, '5446 - Sals Post-Doc RA Foreign'), (5460, '5460 - Sals Non-Students Hourly'), (5462, '5462 - Sals Non-Students Salaried'), (5842, '5842 - Speaker and Consult Fee'),
    (5844, '5844 - Invited Speakers Honoraria')
)


# TODO: Settings - would really like all of the following to be editable by funding admins (or even sys admins)
# it should be the same across all units, and doesn't change with the semester
# model with a single entry doesn't seem quite right? django-dbsettings?

# deal with upcoming minimum wage increases (only one at a time)
NEW_MIN_WAGE_DATE = datetime.date(2023, 6, 1) # Update to most recent or upcoming minimum wage increase date, once known
NEW_MIN_WAGE = 16.75 # Update to most recent or upcoming new minimum wage, once known
MIN_WAGE = 15.65 # Update to new minimum wage once another upcoming minimum wage is known 

def get_minimum_wage(date):
    if date >= NEW_MIN_WAGE_DATE:
        return NEW_MIN_WAGE
    else:
        return MIN_WAGE

def get_minimum_wage_error(start_date, end_date):
    message = 'Gross Hourly Rate Must Be At Least Minimum Wage. (Currently: $' + ("%.2f" % get_minimum_wage(datetime.date.today())) + ')'
    if get_minimum_wage(start_date) != get_minimum_wage(end_date):
        message += ' NOTE: A minimum wage increase occurs on ' + NEW_MIN_WAGE_DATE.strftime("%B %d, %Y") + '. Gross Hourly Rate must be at least ' + ("$%.2f" % NEW_MIN_WAGE) + \
                   ' after this date. If you would like to pay below ' + ("$%.2f" % NEW_MIN_WAGE) + ' but above ' + ("$%.2f" % get_minimum_wage(start_date)) + ' for this appointment before ' + \
                   NEW_MIN_WAGE_DATE.strftime("%B %d, %Y") + ", please create a separate request for that time period."
    elif datetime.date.today() < NEW_MIN_WAGE_DATE and start_date >= NEW_MIN_WAGE_DATE:
        message += ' NOTE: Minimum wage increases on ' + NEW_MIN_WAGE_DATE.strftime("%B %d, %Y") + ' to ' + ("$%.2f" % NEW_MIN_WAGE)
    return message

MIN_WEEKS_VACATION = 2
MIN_VACATION_PAY_PERCENTAGE = 4
# unit contacts 
CS_CONTACT = "csrahelp@sfu.ca"
MSE_CONTACT = "mse_admin_assistant@sfu.ca"
ENSC_CONTACT = "enscfin@sfu.ca"
SEE_CONTACT = "fas_admin_manager@sfu.ca"
DEANS_CONTACT = "fas_budget_manager@sfu.ca"
# general ra contact
FAS_CONTACT = "fasra@sfu.ca"
# intro contacts
URA_CONTACT = "fas_academic_relations@sfu.ca"
PD_CONTACT = "fas_postdoc_support@sfu.ca"

class RARequestIntroForm(forms.ModelForm):
    person = PersonField(label='Appointee', required=False, help_text="Please ensure you are appointing the correct student.")
    supervisor = PersonField(label='Hiring Supervisor', required=True)

    position = forms.CharField(max_length=64, required=False, label="Appointee Position Title")
    
    people_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3, 'maxlength':300}), label="Any comments about the Appointee or Hiring Supervisor?")

    student = forms.ChoiceField(required=True, choices=STUDENT_TYPE, widget=forms.RadioSelect, label="Is the appointee a student?")
    coop = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Is the appointee a co-op student?")
    usra = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label=" Is this an Undergraduate Student Research Awards (USRA) faculty supplement?")
    research = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Will the work performed primarily involve research?")
    thesis = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Is the appointment for the student's thesis/project?")

    class Meta:
        model = RARequest
        fields = ('nonstudent', 'first_name', 'last_name', 'email_address', 'person', 'unit', 'hiring_category')
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
        
        config_init = ['people_comments', 'coop', 'usra', 'student', 'thesis', 'research', 'position']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RARequestIntroForm, self).is_valid(*args, **kwargs)

    # TODO: Make sure total pay and hiring category are calculated properly. Javascript only for now.
    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['people_comments', 'coop', 'usra', 'student', 'thesis', 'research', 'position']

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
        
        usra = cleaned_data.get('usra')
        if usra == "True":
            self.cleaned_data['usra'] = True
        else:
            self.cleaned_data['usra'] = False

        student = cleaned_data.get('student')
        coop = cleaned_data.get('coop')
        research = cleaned_data.get('research')
        thesis = cleaned_data.get('thesis')
        error_message = 'You must answer this question.'
        if (student == 'N'):
            if research == None or research == '':
                self.add_error('research', error_message)
        elif (student == 'U' or student == 'M' or student == 'P'):
            if coop == None or coop == '':
                self.add_error('coop', error_message)
            if (student == 'U') and (usra == None or usra == ''):
                self.add_error('usra', error_message)
            if (student == 'M' or student == 'P') or usra=='False':
                if research == None or research == '':
                    self.add_error('research', error_message)
                if research == 'True':
                    if thesis == None or thesis == '':
                        self.add_error('thesis', error_message)

        hiring_category = cleaned_data.get('hiring_category')
        if hiring_category == None or hiring_category == 'None':
            self.add_error('student', 'Please answer all questions to determine hiring category.')


        # remove irrelevant information
        if nonstudent:
            self.cleaned_data['person'] = None
        else:
            self.cleaned_data['first_name'] = ''
            self.cleaned_data['last_name'] = ''
            self.cleaned_data['email_address'] = ''
        if (student=='N'):
            self.cleaned_data['coop'] = False
            self.cleaned_data['thesis'] = False
            self.cleaned_data['usra'] = False
        elif (student=='U' or student == 'M' or student == 'P'):
            if (student=='U' and usra=='True'):
                self.cleaned_data['thesis'] = False
                self.cleaned_data['research'] = False
            else:
                if research=='False':
                    self.cleaned_data['thesis'] = False
                    self.cleaned_data['usra'] = False

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

        if start_date and end_date:
            if end_date < start_date:
                error_message = "Start date must be before end date."
                self.add_error('end_date', error_message)
                self.add_error('start_date', error_message)

class RARequestFundingSourceForm(forms.ModelForm):
    fs1_unit = forms.ChoiceField(required=True, label="Department #1", choices=DEPT_CHOICES)
    fs1_fund = forms.ChoiceField(required=True, label="Fund #1", choices=FUND_CHOICES)
    fs1_project = forms.CharField(required=False, label="Project #1", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs1_amount = forms.DecimalField(required=False, label="Amount of Funding Source #1 to Total Funding", help_text="Amount of all funding sources must add up to total pay.")
    fs1_start_date = forms.DateField(required=False, label="Start Date #1", help_text="Start Date for Funding Source 1")
    fs1_end_date = forms.DateField(required=False,  label="End Date #1", help_text="End Date for Funding Source 1")

    fs2_option = forms.BooleanField(required=False, label="Please select the following if there is an additional funding source")
    fs2_unit = forms.ChoiceField(required=False, label="Department #2", choices=DEPT_CHOICES)
    fs2_fund = forms.ChoiceField(required=False, label="Fund #2", choices=FUND_CHOICES)
    fs2_project = forms.CharField(required=False, label="Project #2", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs2_amount = forms.DecimalField(required=False, label="Amount of Funding Source #2 to Total Funding", help_text="Amount of all funding sources must add up to total pay.")
    fs2_start_date = forms.DateField(required=False, label="Start Date #2", help_text="Start Date for Funding Source 2")
    fs2_end_date = forms.DateField(required=False,  label="End Date #2", help_text="End Date for Funding Source 2")

    fs3_option = forms.BooleanField(required=False, label="Please select the following if there is an additional funding source")
    fs3_unit = forms.ChoiceField(required=False, label="Department #3", choices=DEPT_CHOICES)
    fs3_fund = forms.ChoiceField(required=False, label="Fund #3", choices=FUND_CHOICES)
    fs3_project = forms.CharField(required=False, label="Project #3", help_text="Example: N654321, S654321, X654321, R654321. If fund 11, you may leave blank.")
    fs3_amount = forms.DecimalField(required=False, label="Amount of Funding Source #3 to Total Funding", help_text="Amount of all funding sources must add up to total pay.")
    fs3_start_date = forms.DateField(required=False, label="Start Date #3", help_text="Start Date for Funding Source 3")
    fs3_end_date = forms.DateField(required=False,  label="End Date #3", help_text="End Date for Funding Source 3")

    class Meta:
        model = RARequest
        fields = ('fs1_unit', 'fs2_unit', 'fs3_unit', 'fs1_fund', 'fs2_fund', 'fs3_fund',
                  'fs1_project', 'fs2_project', 'fs3_project')

    def __init__(self, *args, **kwargs):
        super(RARequestFundingSourceForm, self).__init__(*args, **kwargs)
        config_init = ['fs1_amount', 'fs2_option', 'fs2_amount', 'fs3_option', 'fs3_amount']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

    def clean(self):
        cleaned_data = super(RARequestFundingSourceForm, self).clean()
  
        config_clean = ['fs1_amount', 'fs2_option', 'fs2_amount', 'fs3_option', 'fs3_amount']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        # for fund 11s, do not require fund
        project_exception_fund = '11'

        fs1_fund = cleaned_data.get('fs1_fund')
        fs1_project = cleaned_data.get('fs1_project')

        if fs1_fund != project_exception_fund and (fs1_project == None or fs1_project == ''):
            self.add_error('fs1_project', 'You must answer this question.')

        # add error messages
        total_pay = self.initial['total_pay']
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
        fs1_amount = cleaned_data.get('fs1_amount')
        fs2_amount = cleaned_data.get('fs2_amount')
        fs3_amount = cleaned_data.get('fs3_amount')

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
            if fs1_amount == None or fs1_amount == '':
                self.add_error('fs1_amount', error_message)
            if fs2_amount == None or fs2_amount == '':
                self.add_error('fs2_amount', error_message)

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
            if fs3_amount == None or fs3_amount == '':
                self.add_error('fs3_amount', error_message)

        error_message = "Combined Amount of all Funding Sources Must Add Up to Total Pay"
        if fs2_option and not fs3_option:
            if fs1_amount and fs2_amount:
                amount_sum = fs1_amount + fs2_amount
                if amount_sum != total_pay:
                    self.add_error('fs1_amount', error_message + ". Currently adds to: " + ("$%.2f" % amount_sum))
                    self.add_error('fs2_amount', error_message + ". Currently adds to: " + ("$%.2f" % amount_sum))
        if fs2_option and fs3_option:
            if fs1_amount and fs2_amount and fs3_amount:
                amount_sum = fs1_amount + fs2_amount + fs3_amount
                if amount_sum != total_pay:
                    self.add_error('fs1_amount', error_message + ". Currently adds to: " + ("$%.2f" % amount_sum))
                    self.add_error('fs2_amount', error_message + ". Currently adds to: " + ("$%.2f" % amount_sum))
                    self.add_error('fs3_amount', error_message + ". Currently adds to: " + ("$%.2f" % amount_sum))
        
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
        
        error_message = "Funding source amounts should be greater than 0."
        if fs2_option:
            if fs1_amount == 0:
                self.add_error('fs1_amount', error_message)          
            if fs2_amount == 0:
                self.add_error('fs2_amount', error_message)
        if fs3_option:
            if fs3_amount == 0:
                self.add_error('fs3_amount', error_message)
        
        start_date = cleaned_data.get('start_date')
        fs1_start_date = cleaned_data.get('fs1_start_date')
        fs2_start_date = cleaned_data.get('fs2_start_date')
        fs3_start_date = cleaned_data.get('fs3_start_date')

        # remove irrelevant information
        if not fs3_option: 
            self.cleaned_data['fs3_unit'] = 0
            self.cleaned_data['fs3_fund'] = 0
            self.cleaned_data['fs3_project'] = ''
            self.cleaned_data['fs3_amount'] = 0
            self.cleaned_data['fs3_start_date'] = ''
            self.cleaned_data['fs3_end_date'] = ''

        if not fs2_option:
            self.cleaned_data['fs1_start_date'] = ''
            self.cleaned_data['fs1_end_date'] = ''
            self.cleaned_data['fs1_amount'] = total_pay

            self.cleaned_data['fs2_unit'] = 0
            self.cleaned_data['fs2_fund'] = 0
            self.cleaned_data['fs2_project'] = ''
            self.cleaned_data['fs2_amount'] = 0
            self.cleaned_data['fs2_start_date'] = ''
            self.cleaned_data['fs2_end_date'] = ''

class RARequestGraduateResearchAssistantForm(forms.ModelForm):
    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)

    # fill out if backdated
    backdated = forms.BooleanField(required=False, widget=forms.HiddenInput)
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum", max_digits=8, decimal_places=2)
    backdate_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':10, 'maxlength':500}), label="Please provide the reason for this backdated appointment")

    gras_payment_method = forms.ChoiceField(required=False,
                                            choices=GRAS_PAYMENT_METHOD_CHOICES, 
                                            widget=forms.RadioSelect, 
                                            label="Scholarship (No added benefit & vacation cost)")
    total_gross = forms.DecimalField(required=False, label="Total Funding Provided")
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    scholarship_confirmation_1 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="a) primarily contribute to the student’s academic progress, for example by inclusion in the student’s thesis?")
    scholarship_confirmation_2 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="b) primarily contribute to or benefit someone other than the student, for example by supporting your research program or the grant?")
    scholarship_confirmation_3 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label=mark_safe("c) <u>are not</u> meant to be included in the student’s thesis?"))
    scholarship_confirmation_4 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label=mark_safe("d) <u>are not</u> meant to be part of the student’s education in the student’s academic discipline?"))
    scholarship_confirmation_5 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="a) ask the student to perform research or research-related activities at specific times or places?")
    scholarship_confirmation_6 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="b) require the student to track and/or report the hours during which the student is performing research or research-related activities?")
    scholarship_confirmation_7 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="c) ask or expect the student to perform a specified amount of research or research-related activities in a given week?")
    scholarship_confirmation_8 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="d) ask the student to discuss with you on a regular basis their research and/or research related activities for any reason other than supporting the student’s academic progress?")
    scholarship_confirmation_9 = forms.ChoiceField(required=True, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="e) ask the student to train or otherwise support other researchers in your research group for any reason other than supporting the student’s academic progress?")
    scholarship_subsequent = forms.BooleanField(required=False, label="Check if subsequent semester appointments will have the same answers to these questions")
    scholarship_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':10, 'maxlength':500}), label="Any important notes below")


    class Meta:
        model = RARequest
        fields = ('gras_payment_method', 'total_pay', 'total_gross', 'biweekly_salary')
        widgets = {
            'total_pay': forms.HiddenInput(),     
        }
    
    def __init__(self, complete=False, *args, **kwargs):
        super(RARequestGraduateResearchAssistantForm, self).__init__(*args, **kwargs)
        
        config_init = ['backdate_lump_sum', 'backdate_hours', 'backdate_reason', 'scholarship_confirmation_1', 'scholarship_confirmation_2',
                       'scholarship_confirmation_3', 'scholarship_confirmation_4', 'scholarship_confirmation_5', 'scholarship_confirmation_6', 
                       'scholarship_confirmation_7', 'scholarship_confirmation_8', 'scholarship_confirmation_9', 'scholarship_subsequent', 'scholarship_notes']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

        if complete: 
            scholarship_confirmation_list = ['scholarship_confirmation_1', 'scholarship_confirmation_2', 'scholarship_confirmation_3', 
                                             'scholarship_confirmation_4', 'scholarship_confirmation_5', 'scholarship_confirmation_6', 
                                             'scholarship_confirmation_7', 'scholarship_confirmation_8', 'scholarship_confirmation_9']
            for question in scholarship_confirmation_list:
                self.fields[question].required=False

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['backdate_reason', 'scholarship_confirmation_1', 'scholarship_confirmation_2',
                       'scholarship_confirmation_3', 'scholarship_confirmation_4', 'scholarship_confirmation_5', 'scholarship_confirmation_6', 
                       'scholarship_confirmation_7', 'scholarship_confirmation_8', 'scholarship_confirmation_9', 'scholarship_subsequent', 'scholarship_notes']

        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

        # add error messages
        error_message = "You must answer this question."

        gras_payment_method = cleaned_data.get('gras_payment_method')
        total_gross = cleaned_data.get('total_gross')
        biweekly_salary = cleaned_data.get('biweekly_salary')
        
        backdated = self.initial["backdated"]
        backdate_lump_sum = cleaned_data.get('backdate_lump_sum')
        backdate_reason = cleaned_data.get('backdate_reason')

        start_date = self.initial['start_date']
        end_date = self.initial['end_date']

        if backdated:
            if backdate_lump_sum == 0 or backdate_lump_sum == None or backdate_lump_sum == '':
                self.add_error('backdate_lump_sum', error_message)          
            if backdate_reason == '' or backdate_reason == None:
                self.add_error('backdate_reason', error_message)
        elif gras_payment_method == None or gras_payment_method == "":
            self.add_error('gras_payment_method', error_message)
        else:
            if gras_payment_method == "LE":
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
            if gras_payment_method == "BW":
                if total_gross == 0 or total_gross == None:
                    self.add_error('total_gross', error_message)
    
        scholarship_confirmation_list = ['scholarship_confirmation_1', 'scholarship_confirmation_2', 'scholarship_confirmation_3', 
                                         'scholarship_confirmation_4', 'scholarship_confirmation_5', 'scholarship_confirmation_6', 
                                         'scholarship_confirmation_7', 'scholarship_confirmation_8', 'scholarship_confirmation_9']
        for question in scholarship_confirmation_list:
            q = cleaned_data.get(question)
            if q == "True":
                self.cleaned_data[question] = True
            elif q == "False":
                self.cleaned_data[question] = False

        # remove irrelevant information
        if backdated:
            self.cleaned_data["gras_payment_method"] = ''
            self.cleaned_data["total_gross"] = 0
            self.cleaned_data["weeks_vacation"] = 0
            self.cleaned_data["biweekly_hours"] = 0
            self.cleaned_data["biweekly_salary"] = 0
            self.cleaned_data["vacation_hours"] = 0
            self.cleaned_data["gross_hourly"] = 0
            self.cleaned_data["vacation_pay"] = 0
        else: 
            self.cleaned_data["backdate_lump_sum"] = 0
            self.cleaned_data["backdate_reason"] = ''
            if gras_payment_method == "LE":
                self.cleaned_data['biweekly_salary'] = 0
        # hours always irrelevant for gras
        self.cleaned_data["backdate_hours"] = 0


class RARequestNonContinuingForm(forms.ModelForm):
    # Form for NonContinuing Appointees
    # BiWeekly Payment Method -> total_gross, weeks_vacation, biweekly_hours, should also calculate biweekly_salary, gross_hourly and vacation_hours
    # Hourly Payment Method -> gross_hourly, vacation_pay, biweekly_hours

    pay_periods = forms.DecimalField(required=False, widget=forms.HiddenInput)
    
    # fill out if backdated
    backdated = forms.BooleanField(required=False, widget=forms.HiddenInput)
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum", max_digits=8, decimal_places=2)
    backdate_hours = forms.DecimalField(required=False, label="How many hours is this lump sum based on?", max_digits=8, decimal_places=2)
    backdate_reason = forms.CharField(required=False, label="Please provide the reason for this backdated appointment", widget=forms.Textarea(attrs={'rows':10, 'maxlength': 500}))
    swpp = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Are you planning to apply for student wage subsidy through the Student Work Placement Program (SWPP)?",
                             help_text=mark_safe('<a href="https://www.sfu.ca/hire/covid19/funding.html">Please click here for information about SWPP</a>'))
    nc_duties = forms.CharField(required=False, label="Duties", help_text="Please enter duties in a comma-separated list.", widget=forms.Textarea(attrs={'rows':10, 'maxlength': 900}))
    
    nc_payment_method = forms.ChoiceField(required=False, choices=RA_PAYMENT_METHOD_CHOICES, widget=forms.RadioSelect, label="Please select from the following")

    total_gross = forms.DecimalField(required=False, label="Total Gross Salary Paid")
    weeks_vacation = forms.DecimalField(required=False, label="Weeks Vacation (Minimum 2)")
    biweekly_hours = forms.DecimalField(required=False, label="Bi-Weekly Hours")
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    vacation_hours = forms.DecimalField(required=False, widget=forms.HiddenInput)
    gross_hourly = forms.DecimalField(required=False, label="Gross Hourly Rate ($)")
    vacation_pay = forms.DecimalField(required=False, label="Vacation Pay % (Minimum 4%)")

    class Meta:
        model = RARequest
        fields = ('nc_payment_method', 'total_pay', 'backdated', 'total_gross','weeks_vacation','biweekly_hours',
                  'biweekly_salary','vacation_hours','gross_hourly','vacation_pay')

        widgets = {
            'total_pay': forms.HiddenInput(),     
        }

    def __init__(self, coop=False, *args, **kwargs):
        super(RARequestNonContinuingForm, self).__init__(*args, **kwargs) 
        
        config_init = ['nc_duties', 'backdate_lump_sum', 'backdate_hours', 'backdate_reason', 'swpp']

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)

        if not coop:
            self.fields['swpp'].widget=forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['nc_duties', 'backdate_reason', 'swpp']

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
        vacation_pay = cleaned_data.get('vacation_pay')
        biweekly_hours = cleaned_data.get('biweekly_hours')
        
        backdated = self.initial["backdated"]
        backdate_lump_sum = cleaned_data.get('backdate_lump_sum')
        backdate_hours = cleaned_data.get('backdate_hours')
        backdate_reason = cleaned_data.get('backdate_reason')
        
        start_date = self.initial['start_date']
        end_date = self.initial['end_date']

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
                if float(gross_hourly) < get_minimum_wage(end_date):
                    message = get_minimum_wage_error(start_date, end_date)
                    raise forms.ValidationError(message)
            if nc_payment_method == "H":
                if gross_hourly == None:
                    self.add_error('gross_hourly', error_message)
                elif float(gross_hourly) < get_minimum_wage(end_date):
                    message = get_minimum_wage_error(start_date, end_date)
                    raise forms.ValidationError(message)
                if vacation_pay == None:
                    self.add_error('vacation_pay', error_message)
                elif vacation_pay < MIN_VACATION_PAY_PERCENTAGE:
                    self.add_error('vacation_pay', ('Vacation Pay Must Be At Least % ' + str(MIN_VACATION_PAY_PERCENTAGE)))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)

        swpp = cleaned_data.get('swpp')
        if swpp == "True":
            self.cleaned_data["swpp"] = True
        else:
            self.cleaned_data["swpp"] = False

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
    backdate_lump_sum = forms.DecimalField(required=False, label="As this is a backdated appointment, please provide a lump sum", max_digits=8, decimal_places=2)
    backdate_hours = forms.DecimalField(required=False, label="How many hours is this lump sum based on?", max_digits=8, decimal_places=2)
    backdate_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':10, 'maxlength':500}), label="Please provide the reason for this backdated appointment")
    
    ra_payment_method = forms.ChoiceField(required=False, choices=RA_PAYMENT_METHOD_CHOICES, widget=forms.RadioSelect, label="Please select from the following")
    
    total_gross = forms.DecimalField(required=False, label="Total Gross Salary Paid")
    weeks_vacation = forms.DecimalField(required=False, label="Weeks Vacation (Minimum 2)")
    biweekly_hours = forms.DecimalField(required=False, label="Bi-Weekly Hours")
    biweekly_salary = forms.DecimalField(required=False, widget=forms.HiddenInput)
    vacation_hours = forms.DecimalField(required=False, widget=forms.HiddenInput)
    gross_hourly = forms.DecimalField(required=False, label="Gross Hourly Rate ($)")
    vacation_pay = forms.DecimalField(required=False, label="Vacation Pay % (Minimum 4%)")
    
    ra_benefits = forms.ChoiceField(required=True, choices=RA_BENEFITS_CHOICES, widget=forms.RadioSelect, 
                                    label='Are you willing to provide extended health benefits?', 
                                    help_text=mark_safe('<a href="http://www.sfu.ca/content/dam/sfu/human-resources/forms-documents/benefits/Research_PDF/Research%20Benefit%20Summary%20-%20Fall%202023.pdf">Please click here and refer to "Summary of RA Benefit Plan" for the cost of each medical and dental care plan</a>'))

    swpp = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=BOOL_CHOICES, label="Are you planning to apply for student wage subsidy through the Student Work Placement Program (SWPP)?",
                             help_text=mark_safe('<a href="https://www.sfu.ca/hire/covid19/funding.html">Please click here for information about SWPP</a>'))

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
    ra_other_duties = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3, 'maxlength':300}), label="Other RA Duties")

    class Meta:
        model = RARequest
        fields = ('ra_payment_method', 'total_pay', 'backdated', 'total_gross','weeks_vacation','biweekly_hours',
                  'biweekly_salary','vacation_hours','gross_hourly','vacation_pay')

        widgets = {
            'total_pay': forms.HiddenInput() 
        }

    def __init__(self, coop=False, usra=False, *args, **kwargs):
        super(RARequestResearchAssistantForm, self).__init__(*args, **kwargs)
        
        config_init = ['ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 
                'ra_duties_eq', 'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 
                'ra_benefits', 'ra_other_duties', 'backdate_lump_sum', 'backdate_hours', 'backdate_reason', 'swpp']
        
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
        
        if not coop or usra:
            self.fields['swpp'].widget=forms.HiddenInput()
        if usra: 
            self.fields['ra_benefits'].widget=forms.HiddenInput()
            self.fields['ra_benefits'].required=False

    def clean(self):
        cleaned_data = super().clean()

        config_clean = ['ra_payment_method', 'ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 
                'ra_duties_eq', 'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 'ra_benefits', 'ra_other_duties', 
                'backdate_reason', 'swpp']

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
                
        start_date = self.initial['start_date']
        end_date = self.initial['end_date']

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
                if float(gross_hourly) < get_minimum_wage(end_date):
                    message = get_minimum_wage_error(start_date, end_date)
                    raise forms.ValidationError(message)
            elif ra_payment_method == "H":
                if gross_hourly == None:
                    self.add_error('gross_hourly', error_message)
                elif float(gross_hourly) < get_minimum_wage(end_date):
                    message = get_minimum_wage_error(start_date, end_date)
                    raise forms.ValidationError(message)
                if vacation_pay == None:
                    self.add_error('vacation_pay', error_message)
                elif vacation_pay < MIN_VACATION_PAY_PERCENTAGE:
                    self.add_error('vacation_pay', ('Vacation Pay Must Be At Least % ' + str(MIN_VACATION_PAY_PERCENTAGE)))
                if biweekly_hours == None or biweekly_hours == 0:
                    self.add_error('biweekly_hours', error_message)

        swpp = cleaned_data.get('swpp')
        if swpp == "True":
            self.cleaned_data["swpp"] = True
        else:
            self.cleaned_data["swpp"] = False

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
            
class ShortClearableFileInput(forms.ClearableFileInput):
    """
    File input that has the "clear" checkbox, but with no link to the file and only the file name (no file path).
    Adapted from CleanClearableFileInput in quizzes/types/file.py
    """

    template_name = 'short_clearable_file_input.html'

    def format_value(self, value):
        # format as just the filename
        if value and value.name:
            _, filename = os.path.split(value.name)
            return filename
        else:
            return 'none'

class RARequestSupportingForm(forms.ModelForm):
    funding_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3, 'maxlength':500}), label="Any comments about funding?")
    
    class Meta:
        model = RARequest
        fields = ('file_attachment_1', 'file_attachment_2',)
        labels = {'file_attachment_1': "Supplementary Document #1",
                  'file_attachment_2': "Supplementary Document #2",
        }
        widgets = {
            'file_attachment_1': ShortClearableFileInput,
            'file_attachment_2': ShortClearableFileInput
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
    additional_supervisor = forms.CharField(required=False, label="Co-Signing Supervisor (Optional)", help_text="Please fill out both supervisor and department field if there is a co-signer.")
    additional_department = forms.CharField(required=False, label="Co-Signing Department (Optional)", help_text="Please fill out both supervisor and department field if there is a co-signer.")
   
    class Meta:
        model = RARequest
        fields = ('offer_letter_text',)
        widgets = {
                   'offer_letter_text': forms.Textarea(attrs={'rows': 25, 'cols': 70}),
                   }

    def __init__(self, *args, **kwargs):
        super(RARequestLetterForm, self).__init__(*args, **kwargs)
        config_init = ['additional_supervisor', 'additional_department']
        
        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
    
    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['additional_supervisor', 'additional_department']
        for field in config_clean:
            setattr(self.instance, field, cleaned_data[field])

class RARequestScienceAliveForm(forms.Form):
    letter_type = forms.ChoiceField(required=True, choices=SCIENCE_ALIVE_TYPE, widget=forms.RadioSelect, label="Type Of Science Alive Letter")
    final_bullet = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':6, 'maxlength': 500}), help_text="Leave blank if none.", 
                                   label="If you have anything to add in an additional bullet point, please enter here")
    
class RARequestAdminPAFForm(forms.ModelForm):
    position_no = forms.IntegerField(required=False, label="Position #")
    object_code = forms.ChoiceField(required=False, label="Object Code for Funding Sources", choices=OBJECT_CHOICES)
    paf_comments = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':6, 'maxlength':305}), label="Comments", help_text = "Maximum of 305 characters")
    encumbered_hours = forms.DecimalField(required=False, label="Alternate Encumbered Hours")
    fs1_program = forms.ChoiceField(required=False, label="Program for Funding Source #1", choices=PROGRAM_CHOICES)
    fs2_program = forms.ChoiceField(required=False, label="Program for Funding Source #2", choices=PROGRAM_CHOICES)
    fs3_program = forms.ChoiceField(required=False, label="Program for Funding Source #3", choices=PROGRAM_CHOICES)
    fs1_biweekly_rate = forms.DecimalField(required=False, label="Bi-Weekly Rate for Funding Source #1")
    fs1_percentage = forms.DecimalField(required=False, label="Percentage for Funding Source #1")
    fs2_biweekly_rate = forms.DecimalField(required=False, label="Bi-Weekly Rate for Funding Source #2")
    fs2_percentage = forms.DecimalField(required=False, label="Percentage for Funding Source #2")
    fs3_biweekly_rate = forms.DecimalField(required=False, label="Bi-Weekly Rate for Funding Source #3")
    fs3_percentage = forms.DecimalField(required=False, label="Percentage for Funding Source #3")

    class Meta:
        model = RARequest
        fields = ()

    def __init__(self, *args, **kwargs):
        super(RARequestAdminPAFForm, self).__init__(*args, **kwargs)
        config_init = ['position_no', 'object_code', 'fs1_program', 'fs2_program', 'fs3_program',
                       'fs1_percentage', 'fs2_percentage', 'fs3_percentage', 'encumbered_hours',
                       'fs1_biweekly_rate', 'fs2_biweekly_rate', 'fs3_biweekly_rate', 'paf_comments']
        

        for field in config_init:
            self.initial[field] = getattr(self.instance, field)
    
    def clean(self):
        cleaned_data = super().clean()
        config_clean = ['position_no', 'object_code', 'fs1_program', 'fs2_program', 'fs3_program',
                       'fs1_percentage', 'fs2_percentage', 'fs3_percentage', 'encumbered_hours',
                       'fs1_biweekly_rate', 'fs2_biweekly_rate', 'fs3_biweekly_rate', 'paf_comments']

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
    current = forms.BooleanField(label='Only current appointments', initial=False, help_text='Appointments active now (or within two weeks).')


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
