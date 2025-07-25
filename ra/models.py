from django.db import models
from django.urls import reverse
from coredata.models import Person, Unit, Semester, Role
from visas.models import Visa
from courselib.json_fields import JSONField, config_property
from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from grad.models import Scholarship
from courselib.text import normalize_newlines
from courselib.storage import UploadedFileStorage, upload_path
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import datetime, os, uuid, math

# general ra contact
FAS_CONTACT = "fasra@sfu.ca"

HIRING_CATEGORY_CHOICES = (
    ('U', 'Undergrad'),
    ('E', 'Grad Employee'),
    ('N', 'Non-Student'),
    ('S', 'Grad Scholarship'),
    ('RA', 'Research Assistant'),
    ('RSS', 'Research Services Staff'),
    ('PDF', 'Post Doctoral Fellow'),
    ('ONC', 'Other Non Continuing'),
    ('RA2', 'University Research Assistant (Min of 2 years with Benefits)'),
    ('RAR', 'University Research Assistant (Renewal after 2 years with Benefits)'),
    ('GRA', 'Graduate Research Assistant'),
    ('NS', 'National Scholarship'),
    )
HIRING_CATEGORY_DISABLED = set(['U','E','N','S']) # hiring categories that cannot be selected for new contracts


#PAY_TYPE_CHOICES = (
#    ('H', 'Hourly'),
#    ('B', 'Biweekly'),
#    ('L', 'Lump Sum'),
#    )

PAY_FREQUENCY_CHOICES = (
    ('B', 'Biweekly'),
    ('L', 'Lump Sum'),
)


# If a RA is within SEMESTER_SLIDE days of the border
# of a semester, it is pushed into that semester.
# This is to prevent RAs that are, for example, 2 days into
# the Summer semester from being split into two equal-pay
# chunks. 
SEMESTER_SLIDE = 15


class ProgramQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)

    def visible_by_unit(self, units):
        return self.visible().filter(unit__in=units)


class Program(models.Model):
    """
    A field required for the new Chart of Accounts
    """
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    program_number = models.PositiveIntegerField()
    title = models.CharField(max_length=60)
    objects = ProgramQueryset.as_manager()

    def autoslug(self):
        return make_slug(self.unit.label + '-' + str(self.program_number).zfill(5))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False)

    class Meta:
        ordering = ['program_number']

    def __str__(self):
        return "%05d, %s" % (self.program_number, self.title)

    def delete(self, *args, **kwargs):
        self.hidden = True
        self.save()

    def get_program_number_display(self):
        return str(self.program_number).zfill(5)


class Project(models.Model):
    """
    A table to look up the appropriate fund number based on the project number
    """
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    department_code = models.PositiveIntegerField(default=0)
    project_prefix = models.CharField("Prefix", max_length=1, null=True, blank=True,
                                      help_text="If the project number has a prefix of 'R', 'X', etc, add it here")
    project_number = models.PositiveIntegerField(null=True, blank=True)
    fund_number = models.PositiveIntegerField()
    def autoslug(self):
        return make_slug(self.unit.label + '-' + str(self.project_number))
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False)
    
    class Meta:
        ordering = ['project_number']

    def __str__(self):
        return "%06i (%s) - %s" % (self.department_code, self.fund_number, self.project_number)

    def delete(self, *args, **kwargs):
        self.hidden = True
        self.save()

    def get_full_project_number(self):
        if self.project_number:
            return (self.project_prefix or '').upper() + str(self.project_number).zfill(6)
        else:
            return ''

class Account(models.Model):
    """
    A table to look up the appropriate position number based on the account number.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    account_number = models.PositiveIntegerField()
    position_number = models.PositiveIntegerField()
    title = models.CharField(max_length=60)
    def autoslug(self):
        return make_slug(self.unit.label + '-' + str(self.account_number) + '-' + str(self.title))
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False)

    class Meta:
        ordering = ['account_number']

    def __str__(self):
        return "%06i (%s)" % (self.account_number, self.title)

    def delete(self, *args, **kwargs):
        self.hidden = True
        self.save()

#  The built-in default letter templates
DEFAULT_LETTER = '\n\n'.join([
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from income. You should set aside funds to cover your eventual income tax obligation.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """Hours of work: There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed 40 hours per week.""",
        """Mandatory SFU Safety Orientation Training: WorkSafe BC requires all new graduate students to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
        ])
DEFAULT_LETTER_LUMPSUM = "This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s, will be a Lump Sum payment of $%(lump_sum_pay)s.\n\n" + DEFAULT_LETTER
DEFAULT_LETTER_BIWEEKLY = "This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s. The remuneration will be a biweekly payment of $%(biweekly_pay)s for a total amount of $%(lump_sum_pay)s inclusive of 4%% vacation.\n\n" \
    + DEFAULT_LETTER

DEFAULT_LETTER_NON_STUDENT = '\n\n'.join([
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """Any earnings paid by Canadian Sources are subject to the regulations set out by the Canada Revenue Agency (CRA). By law, deductions are taken from the salary for Canada Income Tax, Canada Pension Plan (CPP) and Employment Insurance (EI).""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """Hours of work: There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed 40 hours per week.""",
        """Mandatory SFU Safety Orientation Training: WorkSafe BC requires all new graduate students to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
        ])
DEFAULT_LETTER_NON_STUDENT_LUMPSUM = "This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s, will be a Lump Sum payment of $%(lump_sum_pay)s and subject to all statutory income tax and benefit deductions.\n\n" + DEFAULT_LETTER_NON_STUDENT
DEFAULT_LETTER_NON_STUDENT_BIWEEKLY = "This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s. The remuneration will be a biweekly payment of $%(biweekly_pay)s for a total amount of $%(lump_sum_pay)s inclusive of 4%% vacation and subject to all statutory income tax and benefit deductions.\n\n" \
    + DEFAULT_LETTER_NON_STUDENT

DEFAULT_LETTER_POSTDOC = '\n\n'.join([
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02 and 50.03, which can be found on the SFU website.""",
        """Hours of work: There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed 40 hours per week.""",
        """Mandatory SFU Safety Orientation Training: WorkSafe BC requires all new graduate students to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
        ])
DEFAULT_LETTER_POSTDOC_LUMPSUM = "This is to confirm remuneration of work performed as a Postdoctoral Research Assistant from %(start_date)s to %(end_date)s, will be a Lump Sum payment of $%(lump_sum_pay)s and subject to all statutory income tax and benefit deductions.\n\n" + DEFAULT_LETTER_POSTDOC
DEFAULT_LETTER_POSTDOC_BIWEEKLY = "This is to confirm remuneration of work performed as a Postdoctoral Research Assistant from %(start_date)s to %(end_date)s. The remuneration will be a biweekly payment of $%(biweekly_pay)s for a total amount of $%(lump_sum_pay)s inclusive of 4%% vacation and subject to all statutory income tax and benefit deductions.\n\n" \
    + DEFAULT_LETTER_POSTDOC

# user-available choices for letters: {key: (name, lumpsum text, biweekly text)}. Key must be URL-safe text
DEFAULT_LETTERS = {
    'DEFAULT': ('Standard RA Letter', DEFAULT_LETTER_LUMPSUM, DEFAULT_LETTER_BIWEEKLY),
    'NONSTUDENT': ('RA Letter for Non-Student', DEFAULT_LETTER_NON_STUDENT_LUMPSUM,
                   DEFAULT_LETTER_NON_STUDENT_BIWEEKLY),
    'POSTDOC': ('RA Letter for Post-Doc', DEFAULT_LETTER_POSTDOC_LUMPSUM, DEFAULT_LETTER_POSTDOC_BIWEEKLY),
}   # note to self: if allowing future configuration per-unit, make sure the keys are globally-unique.


### RA REQUEST (APPLICATIONS)

# offer letters

DEFAULT_LETTER_NCH_INTRO = "This is to confirm remuneration of work performed as a %(position)s from %(start_date)s to %(end_date)s. The remuneration will be $%(gross_hourly)s per hour plus 4 percent vacation pay. You must report your total work hours to your supervisor/delegate on a bi-weekly basis. This remuneration will be subject to all statutory income tax and benefit deductions. Any earnings paid by Canadian Sources are subject to the regulations set out by the Canada Revenue Agency (CRA). By law, deductions are taken from the salary for Canada Income Tax, Canada Pension Plan (CPP) and Employment Insurance (EI).\n\n"
DEFAULT_LETTER_NCBW_INTRO = "This is to confirm remuneration of work performed as a %(position)s from %(start_date)s to %(end_date)s. The remuneration will be a biweekly payment of $%(biweekly_salary)s for a total amount of $%(total_pay)s. This remuneration will be subject to all statutory income tax and benefit deductions. Any earnings paid by Canadian Sources are subject to the regulations set out by the Canada Revenue Agency (CRA). By law, deductions are taken from the salary for Canada Income Tax, Canada Pension Plan (CPP) and Employment Insurance (EI).\n\n"
DEFAULT_LETTER_NCLS_INTRO = "This is to confirm remuneration of work performed as a %(position)s from %(start_date)s to %(end_date)s. The remuneration will be provided to you as a lump sum payment of $%(total_pay)s (inclusive of 4 percent vacation pay in lieu of vacation time) and will be made to you at the end of your term of appointment. This remuneration will be subject to all statutory income tax and benefit deductions. Any earnings paid by Canadian Sources are subject to the regulations set out by the Canada Revenue Agency (CRA). By law, deductions are taken from the salary for Canada Income Tax, Canada Pension Plan (CPP) and Employment Insurance (EI).\n\n"
DEFAULT_LETTER_GRASLE_INTRO_INSIDE_CAN = "This is to confirm your funding as a True Scholarship from %(start_date)s to %(end_date)s. The funding will be provided to you as a lump sum payment of $%(total_gross)s and will be made to you at the end of your term of appointment.\n\n"
DEFAULT_LETTER_GRASBW_INTRO = "This is to confirm your funding as a True Scholarship from %(start_date)s to %(end_date)s. The funding will be provided to you in biweekly payments of $%(biweekly_salary)s for a total amount of $%(total_pay)s.\n\n"

DEFAULT_LETTER_GRAS = '\n\n'.join([
    """This agreement exists solely between you as a student and me as your research supervisor. This does not constitute as an offer of employment from Simon Fraser University.""",
    """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from this income. You should set aside funds to cover your eventual income tax obligation.\n\n""",
    ])
DEFAULT_LETTER_NCH = '\n\n'.join([
    """<u>General Conditions of Employment</u>""",
    """There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed %(biweekly_hours)s hours bi-weekly.""",
    """Your responsibilities and duties (Duties) will be:""",
    """ \u2022 %(nc_duties)s""",
    """<u>Employment Standards Act</u>""",
    """Any terms and conditions of employment which have not been expressly addressed in this letter but which are covered by the ESA, will be dealt with in conformity with the relevant provisions of the ESA: https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01""",
    """<u>Policies</u>""",
    """You are subject to and must comply with all applicable University policies and procedures including but not limited to:""",
    """GP 18 Human Rights Policy\n GP 37 Conflict of Interest\nGP 44 Sexual Violence and Misconduct Prevention, Education and Support\nGP 47 Bullying and Harassment Policy\nI 10.04 Access to Information and Protection of Privacy\nR 30.03 Intellectual Property Policy""",
    """<u>Mandatory SFU Safety Orientation Training</u>""",
    """WorkSafe BC requires all new employees to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.\n\n"""
    ])

DEFAULT_LETTER_NCBW = '\n\n'.join([
    """<u>General Conditions of Employment</u>""",
    """There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed %(biweekly_hours)s hours bi-weekly.""",
    """Your responsibilities and duties (Duties) will be:""",
    """ \u2022 %(nc_duties)s""",
    """This offer includes 2 weeks of paid vacation per calendar year, which will be %(vacation_hours)s hours (%(vacation_hours_formatted)s) prorated for the duration of your appointment.""",
    """<u>Employment Standards Act</u>""",
    """Any terms and conditions of employment which have not been expressly addressed in this letter but which are covered by the ESA, will be dealt with in conformity with the relevant provisions of the ESA: https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01""",
    """<u>Policies</u>""",
    """You are subject to and must comply with all applicable University policies and procedures including but not limited to:""",
    """GP 18 Human Rights Policy\n GP 37 Conflict of Interest\nGP 44 Sexual Violence and Misconduct Prevention, Education and Support\nGP 47 Bullying and Harassment Policy\nI 10.04 Access to Information and Protection of Privacy\nR 30.03 Intellectual Property Policy""",
    """<u>Mandatory SFU Safety Orientation Training</u>""",
    """WorkSafe BC requires all new employees to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.\n\n"""
    ])

DEFAULT_LETTER_NCLS = '\n\n'.join([
    """There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed 80 hours bi-weekly.""",
    """<u>Employment Standards Act</u>""",
    """Any terms and conditions of employment which have not been expressly addressed in this letter but which are covered by the ESA, will be dealt with in conformity with the relevant provisions of the ESA: https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01""",
    """<u>Policies</u>""",
    """You are subject to and must comply with all applicable University policies and procedures including but not limited to:""",
    """GP 18 Human Rights Policy\n GP 37 Conflict of Interest\nGP 44 Sexual Violence and Misconduct Prevention, Education and Support\nGP 47 Bullying and Harassment Policy\nI 10.04 Access to Information and Protection of Privacy\nR 30.03 Intellectual Property Policy""",
    """<u>Mandatory SFU Safety Orientation Training</u>""",
    """WorkSafe BC requires all new employees to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.\n\n"""
    ])

DEFAULT_LETTER_TRAINING = "Mandatory SFU Safety Orientation Training: WorkSafe BC requires all new graduate students to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material.  You shall be informed if any additional training is required.\n\n"
DEFAULT_LETTER_PIDA = """Public Interest Disclosure Act Training - As of December 1, 2024, the provincial government enacted the Public Interest Disclosure Act (PIDA) at research universities in B.C. including SFU. PIDA is provincial legislation that provides a safe, legally protected way for all current and former BC public sector employees to report serious or systemic issues of wrongdoing in the public sector. Employees are required to complete a training module that covers the protections that the law provides for protecting public sector employees who witness or know of serious wrongdoing occurring in their workplace, and outlines the options available for reporting wrongdoing at SFU and to the Ombudsperson. To access the training, please visit: https://learn.bcombudsperson.ca/speaking-up-safely/\n\n"""

DEFAULT_LETTER_CONCLUDE = "If you accept the terms of this letter, please sign and return the letter, retaining the original for your records.\n\n"
DEFAULT_LETTER_CONCLUDE_NC = "If you accept the terms of this appointment, please sign and return the letter, retaining the original for your records.\n\n"

DEFAULT_LETTER_NCH = DEFAULT_LETTER_NCH_INTRO + DEFAULT_LETTER_NCH + DEFAULT_LETTER_PIDA + DEFAULT_LETTER_CONCLUDE_NC
DEFAULT_LETTER_NCBW = DEFAULT_LETTER_NCBW_INTRO + DEFAULT_LETTER_NCBW + DEFAULT_LETTER_PIDA + DEFAULT_LETTER_CONCLUDE_NC
DEFAULT_LETTER_NCLS = DEFAULT_LETTER_NCLS_INTRO + DEFAULT_LETTER_NCLS + DEFAULT_LETTER_CONCLUDE_NC
DEFAULT_LETTER_GRASLE_INSIDE_CAN = DEFAULT_LETTER_GRASLE_INTRO_INSIDE_CAN + DEFAULT_LETTER_GRAS + DEFAULT_LETTER_TRAINING + DEFAULT_LETTER_CONCLUDE
DEFAULT_LETTER_GRASBW = DEFAULT_LETTER_GRASBW_INTRO + DEFAULT_LETTER_GRAS + DEFAULT_LETTER_TRAINING + DEFAULT_LETTER_CONCLUDE

DEFAULT_LETTER_SCIENCE_ALIVE_INTRO = '\n\n'.join([
    """We are pleased to offer you a temporary appointment with Applied Sciences Outreach (with Science AL!VE). Please find enclosed your appointment letter along with the General Privacy and Confidentiality form. Please review and sign where applicable.""",
    """Name: %(name)s (“Employee”)\nPosition Title: %(position)s\nReports to: Coordinator, Outreach Programs\nDuration: %(start_date)s to %(end_date)s\nRemuneration: $%(gross_hourly)s per hour + 4 percent in lieu of vacation time\nHours of work: We expect these hours not to exceed %(biweekly_hours)s hours bi-weekly. Work hours will be assigned and confirmed as needed by Coordinator, Outreach programs. Employees must report total number of work hours to their supervisor/delegate on a bi-weekly basis. No overtime hours may be worked without express pre-approval in writing from your supervisor.\nWork Location: [ENTER WORK LOCATION HERE]""",
    """<u>About the position</u>\n[ENTER POSITION DETAILS HERE]""",
    """Your responsibilities include, but are not limited to:\n\u2022 %(duties)s""",
    """<u>Terms of Contract</u>\n\u2022 You will be provided with vacation pay of four (4) percent (equivalent to 10 days vacation per annum) that will be automatically added to the above hourly rate in each bi-weekly pay period.
    \u2022 Termination of this appointment may be initiated by either party giving two (2) week notice, except in the case of termination for cause.
    \u2022 You are expected to adhere to the employer's policies and procedures at all times while performing your “Duties”.""",
    """<u>Right to Work in Canada</u>\nIf you are not a Canadian citizen or a permanent resident of Canada, you will need to apply to Immigration, Refugee and Citizenship Canada (“IRCC”) for authorization to enter and work in Canada. It is your responsibility to ensure that you are legally entitled, pursuant to IRCC’s requirements, to work at SFU. You are responsible for complying with the Immigration and Refugees Protection Act (“IRPA”) and with the conditions imposed on your study or work permit by IRCC.""",
    """<u>Employment Standards Act</u>\nAny terms and conditions of employment which have not been expressly addressed in this letter but which are covered by the ESA, will be dealt with in conformity with the relevant provisions of the ESA: https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01""",
    """<u>Policies</u>\nYou are subject to and must comply with all applicable University policies and procedures including but not limited to:\nGP 18 Human Rights Policy\nGP 37 Conflict of Interest\nGP 44 Sexual Violence and Misconduct Prevention, Education and Support\nGP 47 Bullying and Harassment Policy\nI 10.04 Access to Information and Protection of Privacy\nR 30.03 Intellectual Property Policy""",
    """<u>Mandatory Training</u>\nSFU Safety Orientation Training - WorkSafe BC requires all new employees to take and complete safety orientation training.  SFU has a short online module you can take here: https://canvas.sfu.ca/enroll/RR8WDW, and periodically offers classroom sessions of the same material. \n\n"""
    """SFU Respectful Working and Learning Environments Training - Simon Fraser University is committed to creating a diverse, equitable and inclusive community where all feel welcome, accepted and appreciated. It will take all of us, working together to maintain an environment of inclusive excellence that we can be proud to be part of. To learn more please visit SFU Inclusive Excellence: https://www.sfu.ca/edi/actions/inclusive-excellence.html. To support this, a training module has been developed for SFU community members to remind us all about our responsibilities in contributing to respectful learning, research and work environments, help us understand what bullying and harassment behaviours are, and ensure we know where to turn for help. The training supports SFU's Bullying & Harassment policy (GP 47) and is aligned with WorkSafeBC requirements. You can access the module here: https://canvas.sfu.ca/enroll/DLXJPD.\n\n"""
    """Public Interest Disclosure Act Training - As of December 1, 2024, the provincial government enacted the Public Interest Disclosure Act (PIDA) at research universities in B.C. including SFU. PIDA is provincial legislation that provides a safe, legally protected way for all current and former BC public sector employees to report serious or systemic issues of wrongdoing in the public sector. Employees are required to complete a training module that covers the protections that the law provides for protecting public sector employees who witness or know of serious wrongdoing occurring in their workplace, and outlines the options available for reporting wrongdoing at SFU and to the Ombudsperson. To access the training, please visit: https://learn.bcombudsperson.ca/speaking-up-safely/\n\n"""
    """You shall be informed if any additional training is required.\n\n"""
])

DEFAULT_LETTER_SCIENCE_ALIVE = DEFAULT_LETTER_SCIENCE_ALIVE_INTRO + DEFAULT_LETTER_CONCLUDE

BOOL_CHOICES = ((True, 'Yes'), (False, 'No'))

STUDENT_TYPE = (
    ('N', 'Appointee is NOT a student'),
    ('U', 'Undergraduate Student'),
    ('M', 'Masters Student'),
    ('P', 'PhD Student')
)

REQUEST_HIRING_CATEGORY = (
    ('GRAS', 'Graduate Research Assistant Scholarship'),
    ('RA', 'Research Assistant'),
    ('NC', 'Other Non-Continuing')
)

GRAS_PAYMENT_METHOD_CHOICES = (
    ('BW', 'Biweekly funding for students with Canadian bank account.'),
    ('LE', 'Lump sum payment for students with Canadian bank account (Funds will be paid at the end of the appointment term)')
)

RA_PAYMENT_METHOD_CHOICES = (
    ('BW', 'Yes (Salaried - The Appointee is entitled to a minimum of 10 vacation days a year. Vacation time will be pro-rated based on the appointment terms.)'),
    ('H', 'No (Hourly - The Appointee will receive 4% vacation pay. Timesheet must be submitted biweekly for the Appointee to be paid.)')
)

NC_PAYMENT_METHOD_CHOICES = (
    ('BW', 'Bi-weekly salary (The Appointee is entitled to a minimum of 10 vacation days a year per FTE. Vacation time will be prorated' +
    ' based on the appointment terms. An additional 11% will be charged for statutory benefits.)'),
    ('H', 'Hourly (4% vacation pay will be deducted from the project in addition to 11% for statutory benefits. Must submit biweekly' +
    ' timesheets in order for the Appointee to be paid.)'),
    ('LS', 'Lump Sum Amount')
)

RA_VACATION_DAYS_CHOICES = (
    ('2W', '2 Weeks Per Year (Legal Minimum)'),
    ('3W', '3 Weeks Per Year'),
    ('4W', '4 Weeks Per Year'),
    ('5W', '5 Weeks Per Year')
)

RA_VACATION_PAY_CHOICES = (
    ('4P', '4% (Legal Minimum)'),
    ('5P', '5%'),
    ('6P', '6%'),
    ('7P', '7%'),
    ('8P', '8%'),
    ('9P', '9%'),
    ('10P', '10%'),
    ('11P', '11%'),
    ('12P', '12%')
)

RA_BENEFITS_CHOICES = (
    ('Y', "Yes (The cost will be shared 75/25 between employer and employee)."),
    ('NE', 'No - My grant is not eligible.'),
    ('N', 'No')
)

DUTIES_CHOICES_EX = (
    (1, 'Assisting with setting up, conducting or running experiments or research work'),
    (2, 'Observing, recording and/or coding data or observations of experimental results and reporting the behaviour of specimens or research participants'),
    (3, 'Performing journal reviewer selection, preparing manuscripts for production and communicating with journal authors, reviewers, etc.'),
    (4, 'Performing literature or archival research'),
    (5, 'Performing surveys and/or conducting interviews'),
    (6, 'Assisting with feed preparation and the daily maintenance and care of study organisms'),
    (7, 'Editing and translating'),
    (8, 'Developing processes, protocols and procedures'),
    (9, 'Providing leadership planning and policy advice'),
    (10, 'Assisting reporting of findings (e.g. presentation, manuscript writing, final report')
)

DUTIES_CHOICES_DC = (
    (1, 'Assisting with/performing data collection, sampling, identification and/or preparation'),
    (2, 'Administering forms or questionnaires and recording and/or coding data or observations'),
    (3, 'Maintaining research related records and databases, entering data according to established protocols'),
    (4, 'Assisting in analysing and interpreting experimental results or research data')
)

DUTIES_CHOICES_PD = (
    (1, 'Assisting in the development of models used for research'),
    (2, 'Assisting with the design of research projects'),
    (3, 'Assisting in defining the overall direction and priorities of research'),
    (4, 'Researching and determining the applicability of new technology and systems related to research project work'),
    (5, 'Designing, modifying and performing research projects'),
    (6, 'Developing operating protocols and safety procedures')
)

DUTIES_CHOICES_IM = (
    (1, 'Organising research information (databases, spreadsheets, written reports, etc.)'),
    (2, 'Assisting in the design and maintenance of research databases and project management systems'),
    (3, 'Performing system design, prototyping and development'),
    (4, 'Performing assigned information and web management tasks'),
    (5, 'Managing research related social media presence')
)

DUTIES_CHOICES_EQ = (
    (1, 'Maintaining research related inventory and distributing supplies'),
    (2, 'Designing, machining, building and integrating specialized research project equipment'),
    (3, 'Setting up, testing, operating and maintaining research project equipment'),
    (4, 'Operating, maintaining and troubleshooting problems with standard equipment'),
    (5, 'Developing Software'),
)

DUTIES_CHOICES_SU = (
    (1, 'Overseeing the progress of projects'),
    (2, 'Supervising, scheduling and training research staff'),
    (3, 'Orientating new employees into routines, procedures and operation of equipment'),
    (4, 'Making recommendations with respect to hiring and providing input into staff performance')
)

DUTIES_CHOICES_WR = (
    (1, 'Assisting with report writing and results presentation'),
    (2, 'Assisting PI with project compliance and ethics and grant applications'),
    (3, 'Contributing to and/or leading policy reports and academic publications')
)

DUTIES_CHOICES_PM = (
    (1, 'Planning and coordinating research related meetings, events and/or liaison'),
    (2, 'Managing project schedule, resources (human, financial and physical) and/or budget and expenditures'),
    (3, 'Overseeing laboratory, fieldwork and/or other research-related logistics'),
    (4, 'Preparing project financial and account reconciliation reports'),
    (5, 'Assisting in running a laboratory, performing tasks such as, purchasing supplies and minor equipment and maintaining associated accounts')
)

def ra_request_attachment_upload_to(instance, filename):
    return upload_path('rarequestattachments', filename)

# altered from pay_periods to display on paf config for reference
def _fund_pay_periods(start_date, end_date):
    """
    Calculate number of pay periods between some start and end dates.
    i.e. number of work days in period / 10
    """
    day = datetime.timedelta(days=1)
    week = datetime.timedelta(days=7)

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date.weekday() == 5:
        start_date += 2*day
    elif start_date.weekday() == 6:
        start_date += day
    if end_date.weekday() == 5:
        end_date -= day
    elif end_date.weekday() == 6:
        end_date -= 2*day

    # number of full weeks (until sameday: last same weekday before end date)
    weeks = ((end_date-start_date)/7).days
    sameday = start_date + weeks*week
    assert sameday <= end_date < sameday + week
    
    # number of days remaining
    days = (end_date - sameday).days
    if sameday.weekday() > end_date.weekday():
        # don't count weekend days in between
        days -= 2
    
    days += 1 # count both start and end days
    result = (weeks*5 + days)/10.0
    
    return result

def _fund_biweekly_rate(pay_periods, amount):
    if pay_periods <= 0 or amount <= 0:
        biweekly_rate = 0
    else: 
        biweekly_rate = amount / pay_periods
    return biweekly_rate

def _fund_percentage(total_biweekly_rate, biweekly_rate):
    if total_biweekly_rate <= 0 or biweekly_rate <= 0:
        percentage = 0
    else:
        percentage = (biweekly_rate / float(total_biweekly_rate)) * 100 
    return percentage

class RARequest(models.Model):
    # swpp - whether or not student is applying for funding with swpp program
    # people_comments - comments about the appointee or supervisor
    # fs1_amount, fs2_amount, fs3_amount - amount of total pay that each funding source makes up
    # fs1_start_date, fs2_start_date, fs3_start_date - start dates of each funding source
    # fs1_end_date, fs2_end_date, fs3_end_date - end dates of each funding source
    # fs2_option - whether or not we have more than one funding source
    # fs3_option - whether or not we have more than two funding sources
    # position_no - position number for appointment, to be filled out by admin for PAF configuration purposes
    # object_code - object code for appointment, to be filled out by admin for PAF configuration purposes
    # encumbered_hours - alternate encumbered hours to be used in PAF
    # fs1_program, fs2_program, fs3_program - programs for each funding source of appointment, to be filled out by admin for PAF configuration purposes
    # fs1_biweekly_rate, fs2_biweekly_rate, fs3_biweekly_rate - biweekly rate for each funding source of appointment, to be filled out by admin for PAF configuration purposes
    # fs1_percentage, fs2_percentage, fs3_percentage - percentages for each funding source of appointment, to be filled out by admin for PAF configuration purposes
    # paf_comments - comments to be filled out by admin for PAF configuration purposes
    # backdate_lump_sum - backdate lump sum amount for appointment
    # backdate_hours - number of hours the backdate appointment is for
    # backdate_reason - reason for backdated appointment
    # funding_comments - comments about funding
    # ra_benefits - benefits for research assistant appointments
    # ra_duties_ex, ra_duties_dc, ra_duties_pd, ra_duties_im, ra_duties_eq, ra_duties_su, ra_duties_wr, ra_duties_pm 
    #   - list of duties of each type for research assistant appointments, stored in an array
    # nc_duties - duties for non-continuing appointments
    # pay_periods - pay periods in this appointment, calculated from dates
    # funding_available, grant_active, salary_allowable, supervisor_check, visa_valid, payroll_collected, paf_signed, admin_notes 
    #   - whether or not each task has been completed
    # scholarship_confirmation_1-9, scholarship_subsequent, and scholarship_notes - these questions were previosity submitted in a separate questionaire by applicants to determine funding purpose, now to be integrated into the form for graduate research assistants only
    person = models.ForeignKey(Person, related_name='rarequest_person', on_delete=models.PROTECT, null=True)

    nonstudent = models.BooleanField(default=False)

    # only needed if no ID for person
    first_name = models.CharField(max_length=32, null=True, blank=True)
    last_name = models.CharField(max_length=32, null=True, blank=True)
    email_address = models.EmailField(max_length=80, null=True, blank=True)
    
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)

    # submitter is not always the same as person created the request
    author = models.ForeignKey(Person, related_name='rarequest_author', on_delete=models.PROTECT, editable=False)
    supervisor = models.ForeignKey(Person, related_name='rarequest_supervisor', on_delete=models.PROTECT)

    config = JSONField(null=False, blank=False, default=dict)

    # student information
    position = models.CharField(max_length=64, default='', null=True, blank=True)
    student = models.CharField(max_length=80, default=None, null=True, choices=STUDENT_TYPE)
    coop = models.BooleanField(null=True, blank=True)
    swpp = config_property('swpp', default=False) # not currently asked
    usra = config_property('usra', default=False) # not currently asked
    mitacs = models.BooleanField(null=True, blank=True)
    research = models.BooleanField(null=True, blank=True)
    thesis = models.BooleanField(null=True, blank=True)

    # comments about supervisor or appointee
    people_comments = config_property('people_comments', default='')

    # hiring category is based on the above student information
    hiring_category = models.CharField(max_length=80, default=None, choices=REQUEST_HIRING_CATEGORY)
    
    # encumbered hours
    encumbered_hours = config_property('encumbered_hours', default='')

    # funding sources
    fs1_unit = models.IntegerField(default=0)
    fs1_fund = models.IntegerField(default=0)
    fs1_project = models.CharField(max_length=10, default='')
    fs1_percentage = config_property('fs1_percentage', default=100)
    fs1_amount = config_property('fs1_amount', default=0)
    fs1_biweekly_rate = config_property('fs1_biweekly_rate', default=0)
    fs1_start_date = config_property('fs1_start_date', default='')
    fs1_end_date = config_property('fs1_end_date', default='')

    fs2_option = config_property('fs2_option', default=False)
    fs2_unit = models.IntegerField(default=0)
    fs2_fund = models.IntegerField(default=0)
    fs2_project = models.CharField(max_length=10, default='')
    fs2_percentage = config_property('fs2_percentage', default=0)
    fs2_amount = config_property('fs2_amount', default=0)
    fs2_biweekly_rate = config_property('fs2_biweekly_rate', default=0)
    fs2_start_date = config_property('fs2_start_date', default='')
    fs2_end_date = config_property('fs2_end_date', default='')

    fs3_option = config_property('fs3_option', default=False)
    fs3_unit = models.IntegerField(default=0)
    fs3_fund = models.IntegerField(default=0)
    fs3_project = models.CharField(max_length=10, default='')
    fs3_percentage = config_property('fs3_percentage', default=0)
    fs3_amount = config_property('fs3_amount', default=0)
    fs3_biweekly_rate = config_property('fs3_biweekly_rate', default=0)
    fs3_start_date = config_property('fs3_start_date', default='')
    fs3_end_date = config_property('fs3_end_date', default='')

    # start and end dates
    start_date = models.DateField(auto_now=False, default=datetime.date.today, auto_now_add=False)
    end_date = models.DateField(auto_now=False, default=datetime.date.today, auto_now_add=False)
    # ... should calculate pay_periods
    pay_periods = config_property('pay_periods', default=0)

    # payment methods
    gras_payment_method = models.CharField(null=True, blank=True, max_length=80, default=None, choices=GRAS_PAYMENT_METHOD_CHOICES)
    ra_payment_method = models.CharField(null=True, blank=True, max_length=80, default=None, choices=RA_PAYMENT_METHOD_CHOICES)
    nc_payment_method = models.CharField(null=True, blank=True, max_length=80, default=None, choices=NC_PAYMENT_METHOD_CHOICES)

    total_gross = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    weeks_vacation = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    biweekly_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    biweekly_salary = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    gross_hourly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    vacation_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    vacation_pay = models.DecimalField(max_digits=8, decimal_places=1, default=0)

    # lump sum appointments 
    lump_sum_hours = config_property('lump_sum_hours', default=0)
    lump_sum_reason = config_property('lump_sum_reason', default='')

    # for backdated appointments
    backdated = models.BooleanField(default=False)
    backdate_lump_sum = config_property('backdate_lump_sum', default=0)
    backdate_hours = config_property('backdate_hours', default=0)
    backdate_reason = config_property('backdate_reason', default='')

    # all payment methods need to calculate total pay
    total_pay = models.DecimalField(max_digits=8, decimal_places=2)

    # file attachments 
    file_attachment_1 = models.FileField(storage=UploadedFileStorage, null=True,
                      upload_to=ra_request_attachment_upload_to, blank=True, max_length=500)
    file_mediatype_1 = models.CharField(max_length=200, default=None, null=True, blank=True, editable=False)
    file_attachment_2 = models.FileField(storage=UploadedFileStorage, null=True,
                      upload_to=ra_request_attachment_upload_to, blank=True, max_length=500)
    file_mediatype_2 = models.CharField(max_length=200, default=None, null=True, blank=True, editable=False)

    # funding comments 
    funding_comments = config_property('funding_comments', default='')

    # ra only options
    ra_benefits = config_property('ra_benefits', default='')
    ra_duties_ex = config_property('ra_duties_ex', default='')
    ra_duties_dc = config_property('ra_duties_dc', default='')
    ra_duties_pd = config_property('ra_duties_pd', default='')
    ra_duties_im = config_property('ra_duties_im', default='')
    ra_duties_eq = config_property('ra_duties_eq', default='')
    ra_duties_su = config_property('ra_duties_su', default='')
    ra_duties_wr = config_property('ra_duties_wr', default='')
    ra_duties_pm = config_property('ra_duties_pm', default='')
    ra_other_duties = config_property('ra_other_duties', default='')

    # nc only options
    nc_duties = config_property('ra_other_duties', default='')

    # gras only options
    scholarship_confirmation_1 = config_property('scholarship_confirmation_1', default='')
    scholarship_confirmation_2 = config_property('scholarship_confirmation_2', default='')
    scholarship_confirmation_3 = config_property('scholarship_confirmation_3', default='')
    scholarship_confirmation_4 = config_property('scholarship_confirmation_4', default='')
    scholarship_confirmation_5 = config_property('scholarship_confirmation_5', default='')
    scholarship_confirmation_6 = config_property('scholarship_confirmation_6', default='')
    scholarship_confirmation_7 = config_property('scholarship_confirmation_7', default='')
    scholarship_confirmation_8 = config_property('scholarship_confirmation_8', default='')
    scholarship_confirmation_9 = config_property('scholarship_confirmation_9', default='')
    scholarship_subsequent = config_property('scholarship_subsequent', default='')
    scholarship_notes = config_property('scholarship_notes', default='')
    
    # admin
    funding_available = config_property('funding_available', default=False)
    grant_active = config_property('grant_active', default=False)
    salary_allowable = config_property('salary_allowable', default=False)
    supervisor_check = config_property('supervisor_check', default=False)
    visa_valid = config_property('visa_valid', default=False)
    payroll_collected = config_property('payroll_collected', default=False)
    paf_signed = config_property('paf_signed', default=False)
    admin_notes = config_property('admin_notes', default='')

    # extra PAF configuration fields for admin
    position_no = config_property('position_no', default='')
    object_code = config_property('object_code', default='')
    fs1_program = config_property('fs1_program', default='')
    fs2_program = config_property('fs2_program', default='')
    fs3_program = config_property('fs3_program', default='')
    paf_comments = config_property('paf_comments', default='')

    # offer letters
    science_alive = models.BooleanField(default=False)
    offer_letter_text = models.TextField(null=True, default='', help_text="Text of the offer letter to be signed by the RA and supervisor.")
    additional_supervisor = config_property('additional_supervisor', default='')
    additional_department = config_property('additional_department', default='')

    # creation, deletion and status
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(null=False, default=False)
    complete = models.BooleanField(null=False, default=False)
    draft = models.BooleanField(null=False, default=False)

    # email reminders
    reminded = config_property('reminded', default=False)
    
    # last updates and processor
    last_updated_at = models.DateTimeField(auto_now=True)
    last_updater = models.ForeignKey(Person, related_name='rarequest_last_updater', default=None, on_delete=models.PROTECT, null=True, editable=False)
    processor = models.ForeignKey(Person, related_name='rarequest_processor', default=None, on_delete=models.PROTECT, null=True, editable=False)

    # all checks need to be checked off for an appointment to be complete
    def get_complete(self):
        if self.funding_available and self.grant_active and self.salary_allowable and self.supervisor_check and self.visa_valid and self.payroll_collected and self.paf_signed:
            return True
        else:
            return False

    # encourage completion of the checklist before downloading the paf
    def get_paf(self):
        if self.funding_available and self.grant_active and self.salary_allowable and self.supervisor_check and self.visa_valid and self.payroll_collected:
            return True
        else:
            return False

    # slugs
    def autoslug(self):
        if self.nonstudent:
            ident = self.first_name + '_' + self.last_name
        else: 
            if self.person:
                if self.person.userid:
                    ident = self.person.userid
                else:
                    ident = str(self.person.emplid)
        return make_slug('request' + '-' + str(self.start_date.year) + '-' + ident)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __str__(self):
        return self.get_name() + " (" + self.slug + ")"

    def duties_list(self):
        duties = []
        duties += [duty for val, duty in DUTIES_CHOICES_EX if val in [int(i) for i in self.ra_duties_ex]]
        duties += [duty for val, duty in DUTIES_CHOICES_DC if val in [int(i) for i in self.ra_duties_dc]]
        duties += [duty for val, duty in DUTIES_CHOICES_PD if val in [int(i) for i in self.ra_duties_pd]]
        duties += [duty for val, duty in DUTIES_CHOICES_IM if val in [int(i) for i in self.ra_duties_im]]
        duties += [duty for val, duty in DUTIES_CHOICES_EQ if val in [int(i) for i in self.ra_duties_eq]]
        duties += [duty for val, duty in DUTIES_CHOICES_SU if val in [int(i) for i in self.ra_duties_su]]
        duties += [duty for val, duty in DUTIES_CHOICES_WR if val in [int(i) for i in self.ra_duties_wr]]
        duties += [duty for val, duty in DUTIES_CHOICES_PM if val in [int(i) for i in self.ra_duties_pm]]
        return duties

    def get_scholarship_confirmation_complete(self):
        """
        Checks if the scholarship confirmation questionnaire has been completed.
        """
        if self.hiring_category != "GRAS":
            return ""
        scholarship_confirmation_list = [self.scholarship_confirmation_1, self.scholarship_confirmation_2, self.scholarship_confirmation_3, 
                                         self.scholarship_confirmation_4, self.scholarship_confirmation_5, self.scholarship_confirmation_6, 
                                         self.scholarship_confirmation_7, self.scholarship_confirmation_8, self.scholarship_confirmation_9]
        for question in scholarship_confirmation_list:
            if question == '':
                return False
        return True

    def build_letter_text(self):
        """
        Builds the appropriate default letter based on hiring category and payment method.
        """

        substitutions = {}
        text = ''

        if self.science_alive: 
            substitutions = {
                    'name': self.get_name(),
                    'start_date': self.start_date.strftime("%B %d, %Y"),
                    'end_date': self.end_date.strftime("%B %d, %Y"),
                    'position': self.position,
                    'gross_hourly': self.gross_hourly,
                    'biweekly_hours': self.biweekly_hours,
                    'duties': self.nc_duties
                }
            text = DEFAULT_LETTER_SCIENCE_ALIVE % substitutions
        else:
            if self.hiring_category == "NC":
                if self.nc_payment_method == "H":
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'position': self.position,
                        'gross_hourly': self.gross_hourly,
                        'biweekly_hours': self.biweekly_hours,
                        'vacation_pay': self.vacation_pay,
                        'nc_duties': self.nc_duties
                    }
                    text = DEFAULT_LETTER_NCH % substitutions
                elif self.nc_payment_method == "BW":
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'position': self.position,
                        'biweekly_salary': self.biweekly_salary,
                        'biweekly_hours': self.biweekly_hours,
                        'weeks_vacation': self.weeks_vacation,
                        'vacation_hours': self.vacation_hours,
                        'vacation_hours_formatted': self.get_vacation_hours(),
                        'total_pay': self.total_pay,
                        'nc_duties': self.nc_duties
                    }
                    text = DEFAULT_LETTER_NCBW % substitutions
                elif self.nc_payment_method == "LS":
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'position': self.position,
                        'total_pay': self.total_pay,
                    }
                    text = DEFAULT_LETTER_NCLS % substitutions
            elif self.hiring_category == "GRAS":
                if self.gras_payment_method == "LE" or self.gras_payment_method == "LS":
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'total_gross': self.total_gross
                    }
                    text = DEFAULT_LETTER_GRASLE_INSIDE_CAN % substitutions
                elif self.gras_payment_method == "BW":
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'biweekly_salary': self.biweekly_salary,
                        'total_pay': self.total_pay,
                    }
                    text = DEFAULT_LETTER_GRASBW % substitutions
                elif self.backdated: 
                    substitutions = {
                        'start_date': self.start_date.strftime("%B %d, %Y"),
                        'end_date': self.end_date.strftime("%B %d, %Y"),
                        'total_gross': '%.2f' % self.backdate_lump_sum
                    }
                    text = DEFAULT_LETTER_GRASLE_INSIDE_CAN % substitutions
                
        letter_text = text % substitutions

        self.offer_letter_text = letter_text

    def letter_paragraphs(self):
        """
        Return list of paragraphs in the letter (for PDF creation)
        """
        text = self.offer_letter_text
        text = normalize_newlines(text)
        return text.split("\n\n")

    # get projects in a comma-separated list
    def get_projects(self):
        projects = []
        if self.fs1_project:
            projects.append(self.fs1_project)
        if self.fs2_option and self.fs2_project:
            projects.append(self.fs2_project)
        if self.fs3_option and self.fs3_project:
            projects.append(self.fs3_project)
        projects = ', '.join(str(p) for p in set(projects))
        return projects

    # get funds in a comma-separated list
    def get_funds(self):
        funds = []
        funds.append(self.fs1_fund)
        if self.fs2_option and self.fs2_fund:
            funds.append(self.fs2_fund)
        if self.fs3_option and self.fs3_fund:
            funds.append(self.fs3_fund)
        funds = ', '.join(str(f) for f in set(funds))
        return funds

    def get_biweekly_hours(self):
        mins = round(60 * (self.biweekly_hours % 1))
        hours = int(self.biweekly_hours)
        if mins != 0:
            biweekly_hours = str(hours) + " hours and " + str(mins) + " minutes"
        else:
            biweekly_hours = str(hours) + " hours"  
        return biweekly_hours
    
    def get_biweekly_salary(self):
        biweekly_salary = self.biweekly_salary
        if self.gross_hourly != 0 and self.biweekly_hours != 0:
            biweekly_salary = self.gross_hourly * self.biweekly_hours
        return biweekly_salary

    def get_vacation_hours(self):
        mins = round(60 * (self.vacation_hours % 1))
        hours = int(self.vacation_hours)
        if mins != 0:
            vacation_hours = str(hours) + " hours and " + str(mins) + " minutes"
        else:
            vacation_hours = str(hours) + " hours"  
        return vacation_hours

    def get_backdate_hours(self):
        mins = round(60 * (self.backdate_hours % 1))
        hours = int(self.backdate_hours)
        if mins != 0:
            backdate_hours = str(hours) + " hours and " + str(mins) + " minutes"
        else:
            backdate_hours = str(hours) + " hours"  
        return backdate_hours

    def get_grant_cost(self):
        grant_cost = float(self.total_pay)
        hiring_category = self.hiring_category
        if hiring_category == "RA":
            ra_benefits = self.ra_benefits
            payment_method = self.ra_payment_method
            if payment_method == "BW":
                if ra_benefits == "Y":
                    grant_cost = grant_cost * 1.17
                elif (ra_benefits == "NE" or ra_benefits == "N"):
                    grant_cost = grant_cost * 1.11
            elif payment_method == "H":
                grant_cost = self.get_base_pay()
                if ra_benefits == "Y":
                    grant_cost = grant_cost * 1.21
                elif (ra_benefits == "NE" or ra_benefits == "N"):
                    grant_cost = grant_cost * 1.15
        return grant_cost
        
    def get_name(self):
        if self.first_name and self.last_name:
            name = "%s %s" % (self.first_name, self.last_name)
        if self.person:
            name = self.person.name()
        return name
    
    def get_sort_name(self):
        if self.first_name and self.last_name:
            name = "%s, %s" % (self.last_name, self.first_name)
        if self.person:
            name = self.person.sortname()
        return name

    def get_first_name(self):
        if self.first_name:
            first_name = self.first_name
        if self.person:
            first_name = self.person.first_name
        return first_name
             
    def get_last_name(self):
        if self.last_name:
            last_name = self.last_name
        if self.person:
            last_name = self.person.last_name
        return last_name

    def get_email_address(self):
        if self.email_address:
            email_address = self.email_address
        if self.person:
            email_address = self.person.email()
        return email_address

    def get_processor(self):
        processor = ""
        if self.processor:
            processor = self.processor.sortname()
        return processor

    def get_id(self):
        ident = "None"
        if not self.nonstudent and self.person.emplid:
            ident = self.person.emplid
        return ident

    def fs1_info(self):
        pay_periods = round(_fund_pay_periods(self.fs1_start_date, self.fs1_end_date), 2)
        biweekly_rate = round(_fund_biweekly_rate(pay_periods, self.fs1_amount), 2)
        percentage = round(_fund_percentage(self.biweekly_salary, biweekly_rate), 2)
        info = {'pay_periods': pay_periods, 'biweekly_rate': biweekly_rate, 'percentage': percentage}
        return info

    def fs2_info(self):
        pay_periods = round(_fund_pay_periods(self.fs2_start_date, self.fs2_end_date), 2)
        biweekly_rate = round(_fund_biweekly_rate(pay_periods, self.fs2_amount), 2)
        percentage = round(_fund_percentage(self.biweekly_salary, biweekly_rate), 2)
        info = {'pay_periods': pay_periods, 'biweekly_rate': biweekly_rate, 'percentage': percentage}
        return info

    def fs3_info(self):
        pay_periods = round(_fund_pay_periods(self.fs3_start_date, self.fs3_end_date), 2)
        biweekly_rate = round(_fund_biweekly_rate(pay_periods, self.fs3_amount), 2)
        percentage = round(_fund_percentage(self.biweekly_salary, biweekly_rate), 2)
        info = {'pay_periods': pay_periods, 'biweekly_rate': biweekly_rate, 'percentage': percentage}
        return info

    def get_cosigner_line(self):
        if self.hiring_category == "RA" or self.hiring_category == "NC":
            line = "I agree to the conditions of employment"
        elif self.hiring_category == "GRAS":
            line = "I agree to the conditions of this contract"
        return line

    def get_encumbered_hours(self):
        if self.backdated:
            return self.backdate_hours
        elif self.biweekly_hours > 0: 
            return self.biweekly_hours
        else:
            return 0

    def get_base_pay(self):
        if self.pay_periods and self.gross_hourly and self.biweekly_hours:
            return self.pay_periods * float(self.gross_hourly) * float(self.biweekly_hours)
        else:
            return 0

    def get_vacation_pay(self):
        if self.vacation_pay:
            return float(self.total_pay) - self.get_base_pay()
        else:
            return 0

    def get_student_status(self):
        if self.student == 'N':
            return "Not A Student"
        elif self.student == 'U':
            return "Undergraduate"
        elif self.student == 'M':
            return "Masters"
        elif self.student == 'P':
            return "PhD"
        else:
            return ""

    # only most recent 2 visas relevant for csvs
    def get_visa_info(self):
        today = datetime.datetime.today()
        appointee_visas = Visa.objects.visible().filter(person=self.person, start_date__lte=today, end_date__gt=today).order_by('start_date')
        if appointee_visas.count() == 0:
            return None
        elif appointee_visas.count() == 1:
            return (appointee_visas[0], None)
        else:
            return (appointee_visas[0], appointee_visas[1])

    def get_absolute_url(self):
        return reverse('ra:view_request', kwargs={'ra_slug': self.slug})
    
    def has_attachments(self):
        return self.attachments.visible().count() > 0

    def status(self):
        if self.complete:
            status = "Appointment"
        else:
            status = "Request"
        return status

    @classmethod
    def semester_guess(cls, date):
        """
        Guess the semester for a date, in the way that financial people do (without regard to class start/end dates)
        Same method as in RAAppointment
        """
        mo = date.month
        if mo <= 4:
            se = 1
        elif mo <= 8:
            se = 4
        else:
            se = 7
        semname = str((date.year-1900)*10 + se)
        return Semester.objects.get(name=semname)

    @classmethod
    def start_end_dates(cls, semester):
        """
        First and last days of the semester, in the way that financial people do (without regard to class start/end dates)
        Same method as in RAAppointment
        """
        return Semester.start_end_dates(semester)
        
    def start_semester(self):
        """
        Guess the starting semester of this appointment
        Same method as in RAAppointment
        """
        start_semester = RARequest.semester_guess(self.start_date)
        # We do this to eliminate hang - if you're starting N days before 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RARequest.start_end_dates(start_semester)
        if end - self.start_date < datetime.timedelta(SEMESTER_SLIDE):
            return start_semester.next_semester()
        return start_semester

    def end_semester(self):
        """
        Guess the ending semester of this appointment
        Same method as in RAAppointment
        """
        end_semester = RARequest.semester_guess(self.end_date)
        # We do this to eliminate hang - if you're starting N days after 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RARequest.start_end_dates(end_semester)
        if self.end_date - start < datetime.timedelta(SEMESTER_SLIDE):
            return end_semester.previous_semester()
        return end_semester

    def semester_length(self):
        """
        The number of semesters this contracts lasts for
        Same method as in RAAppointment
        """
        return self.end_semester() - self.start_semester() + 1

    @classmethod
    def expiring_appointments(cls):
        """
        Get the list of RA Appointments that will expire in the next few weeks so we can send a reminder email
        """
        today = datetime.datetime.now()
        min_age = datetime.datetime.now() + datetime.timedelta(days=28)
        min_age_ras = datetime.datetime.now() + datetime.timedelta(days=60)
        expiring_ras = RARequest.objects.filter(end_date__gt=today, end_date__lte=min_age, hiring_category__in=["GRAS", "NC"], deleted=False, draft=False, complete=True)
        expiring_true_ras = RARequest.objects.filter(end_date__gt=today, end_date__lte=min_age_ras, hiring_category="RA", deleted=False, draft=False, complete=True)
        all_ras = expiring_ras | expiring_true_ras
        ras = [ra for ra in all_ras if 'reminded' not in ra.config or not ra.config['reminded']]
        return ras

    def mark_reminded(self):
        self.config['reminded'] = True
        self.save()

    @classmethod
    def email_expiring_ras(cls):
        """
        Emails the supervisors of the RAs who have appointments that are about to expire.
        Same method as in RAAppointment
        """
        from_email = settings.DEFAULT_FROM_EMAIL

        expiring_ras = cls.expiring_appointments()
        html_template = get_template('ra/emails/new_reminder.html')
        text_template = get_template('ra/emails/new_reminder.txt')

        for raappt in expiring_ras:
            supervisor = raappt.supervisor
            hiring_category = raappt.hiring_category

            if hiring_category == "RA":
                subject = "Research Assistant Appointment Expiry Reminder"
                cc = [FAS_CONTACT]
            elif hiring_category == "GRAS":
                cc = None
                subject = "Graduate RA Scholarship Appointment Expiry Reminder"
                # Let's see if we have any Funding CC supervisors that should also get the reminder.
                fund_cc_roles = Role.objects_fresh.filter(unit=raappt.unit, role='FDCC')
                # If we do, let's add them to the CC list, but let's also make sure to use their role account email for
                # the given role type if it exists.
                if fund_cc_roles:
                    people = []
                    for role in fund_cc_roles:
                        people.append(role.person)
                    people = list(set(people))
                    cc = []
                    for person in people:
                        cc.append(person.role_account_email('FDCC'))
            else:
                subject = "Appointment Expiry Reminder"
                cc = None


            research_assistant = (hiring_category == "RA")
            graduate_research_assistant = (hiring_category == "GRAS")
            non_continuing = (hiring_category == "NC") 
            url = settings.BASE_ABS_URL + raappt.get_absolute_url()
            context = {'supervisor': supervisor, 'raappt': raappt, 'research_assistant': research_assistant, 'graduate_research_assistant': graduate_research_assistant, 'non_continuing': non_continuing, 'url': url}
            text_content = text_template.render(context)
            html_content = html_template.render(context)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [supervisor.email()],
                                         headers={'X-coursys-topic': 'ra'}, cc=cc)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            raappt.mark_reminded()

def ra_request_admin_attachment_upload_to(instance, filename):
    return upload_path('rarequestadminattachments', filename)

class RARequestAttachmentQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)

class RARequestAttachment(models.Model):
    """
    Admins can add attachments to RA Requests.
    """
    req = models.ForeignKey(RARequest, null=False, blank=False, related_name="attachments", on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('req',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=ra_request_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = RARequestAttachmentQueryset.as_manager()

    def __str__(self):
        return self.contents.name + " titled " + self.title + ", for " + str(self.req)

    class Meta:
        ordering = ("created_at",)
        unique_together = (("req", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()

class RAAppointment(models.Model):
    """
    This stores information about a (Research Assistant)s application and pay.
    """
    person = models.ForeignKey(Person, help_text='The RA who is being appointed.', null=False, blank=False, related_name='ra_person', on_delete=models.PROTECT)
    sin = models.PositiveIntegerField(null=True, blank=True)
    # We want do add some sort of accountability for checking visas.
    visa_verified = models.BooleanField(default=False, help_text='I have verified this RA\'s visa information')
    hiring_faculty = models.ForeignKey(Person, help_text='The manager who is hiring the RA.', related_name='ra_hiring_faculty', on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, help_text='The unit that owns the appointment', null=False, blank=False, on_delete=models.PROTECT)
    hiring_category = models.CharField(max_length=4, choices=HIRING_CATEGORY_CHOICES, default='GRA')
    scholarship = models.ForeignKey(Scholarship, null=True, blank=True, help_text='Scholarship associated with this appointment. Optional.', on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=False, blank=False, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, null=False, blank=False, help_text='This is now called "Object" in the new PAF', on_delete=models.PROTECT)
    program = models.ForeignKey(Program, null=True, blank=True, help_text='If none is provided,  "00000" will be added in the PAF', on_delete=models.PROTECT)
    start_date = models.DateField(auto_now=False, auto_now_add=False)
    end_date = models.DateField(auto_now=False, auto_now_add=False)
    pay_frequency = models.CharField(max_length=60, choices=PAY_FREQUENCY_CHOICES, default='B')
    lump_sum_pay = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Total Pay")
    lump_sum_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Total Hours", blank=True, null=True)
    biweekly_pay = models.DecimalField(max_digits=8, decimal_places=2)
    pay_periods = models.DecimalField(max_digits=6, decimal_places=1)
    hourly_pay = models.DecimalField(max_digits=8, decimal_places=2)
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Biweekly Hours")
    reappointment = models.BooleanField(default=False, help_text="Are we re-appointing to the same position?")
    medical_benefits = models.BooleanField(default=False, help_text="50% of Medical Service Plan")
    dental_benefits = models.BooleanField(default=False, help_text="50% of Dental Plan")
    #  The two following fields verbose names are reversed for a reason.  They were named incorrectly with regards to
    #  the PAF we generate, so the verbose names are correct.
    notes = models.TextField("Comments", blank=True, help_text="Biweekly employment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.")
    comments = models.TextField("Notes", blank=True, help_text="For internal use")
    offer_letter_text = models.TextField(null=True, help_text="Text of the offer letter to be signed by the RA and supervisor.")

    def autoslug(self):
        if self.person.userid:
            ident = self.person.userid
        else:
            ident = str(self.person.emplid)
        return make_slug(self.unit.label + '-' + str(self.start_date.year) + '-' + ident)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
    defaults = {'use_hourly': False}
    use_hourly, set_use_hourly = getter_setter('use_hourly')

    def __str__(self):
        return str(self.person) + "@" + str(self.created_at)

    class Meta:
        ordering = ['person', 'created_at']

    def save(self, *args, **kwargs):
        # set SIN field on the Person object
        if self.sin and 'sin' not in self.person.config:
            self.person.set_sin(self.sin)
            self.person.save()
        super(RAAppointment, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('ra:view', kwargs={'ra_slug': self.slug})

    def mark_reminded(self):
        self.config['reminded'] = True
        self.save()

    @staticmethod
    def letter_choices(units):
        """
        Return a form choices list for RA letter templates in these units.

        Ignores the units for now: we want to allow configurability later.
        """
        return [(key, label) for (key, (label, _, _)) in list(DEFAULT_LETTERS.items())]

    def build_letter_text(self, selection):
        """
        This takes the value passed from the letter selector menu and builds the appropriate
        default letter based on that.
        """
        substitutions = {
            'start_date': self.start_date.strftime("%B %d, %Y"),
            'end_date': self.end_date.strftime("%B %d, %Y"),
            'lump_sum_pay': self.lump_sum_pay,
            'biweekly_pay': self.biweekly_pay,
            }

        _, lumpsum_text, biweekly_text = DEFAULT_LETTERS[selection]

        if self.pay_frequency == 'B':
            text = biweekly_text
        else:
            text = lumpsum_text

        letter_text = text % substitutions
        self.offer_letter_text = letter_text
        self.save()

    def letter_paragraphs(self):
        """
        Return list of paragraphs in the letter (for PDF creation)
        """
        text = self.offer_letter_text
        text = normalize_newlines(text)
        return text.split("\n\n") 
    
    @classmethod
    def semester_guess(cls, date):
        """
        Guess the semester for a date, in the way that financial people do (without regard to class start/end dates)
        """
        mo = date.month
        if mo <= 4:
            se = 1
        elif mo <= 8:
            se = 4
        else:
            se = 7
        semname = str((date.year-1900)*10 + se)
        return Semester.objects.get(name=semname)

    @classmethod
    def start_end_dates(cls, semester):
        """
        First and last days of the semester, in the way that financial people do (without regard to class start/end dates)
        """
        return Semester.start_end_dates(semester)
        #yr = int(semester.name[0:3]) + 1900
        #sm = int(semester.name[3])
        #if sm == 1:
        #    start = datetime.date(yr, 1, 1)
        #    end = datetime.date(yr, 4, 30)
        #elif sm == 4:
        #    start = datetime.date(yr, 5, 1)
        #    end = datetime.date(yr, 8, 31)
        #elif sm == 7:
        #    start = datetime.date(yr, 9, 1)
        #    end = datetime.date(yr, 12, 31)
        #return start, end
        
    def start_semester(self):
        "Guess the starting semester of this appointment"
        start_semester = RAAppointment.semester_guess(self.start_date)
        # We do this to eliminate hang - if you're starting N days before 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RAAppointment.start_end_dates(start_semester)
        if end - self.start_date < datetime.timedelta(SEMESTER_SLIDE):
            return start_semester.next_semester()
        return start_semester

    def end_semester(self):
        "Guess the ending semester of this appointment"
        end_semester = RAAppointment.semester_guess(self.end_date)
        # We do this to eliminate hang - if you're starting N days after 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RAAppointment.start_end_dates(end_semester)
        if self.end_date - start < datetime.timedelta(SEMESTER_SLIDE):
            return end_semester.previous_semester()
        return end_semester

    def semester_length(self):
        "The number of semesters this contracts lasts for"
        return self.end_semester() - self.start_semester() + 1

    @classmethod
    def expiring_appointments(cls):
        """
        Get the list of RA Appointments that will expire in the next few weeks so we can send a reminder email
        """
        today = datetime.datetime.now()
        min_age = datetime.datetime.now() + datetime.timedelta(days=14)
        expiring_ras = RAAppointment.objects.filter(end_date__gt=today, end_date__lte=min_age, deleted=False)
        ras = [ra for ra in expiring_ras if 'reminded' not in ra.config or not ra.config['reminded']]
        return ras

    @classmethod
    def email_expiring_ras(cls):
        """
        Emails the supervisors of the RAs who have appointments that are about to expire.
        """
        subject = 'RA appointment expiry reminder'
        from_email = settings.DEFAULT_FROM_EMAIL

        expiring_ras = cls.expiring_appointments()
        template = get_template('ra/emails/reminder.txt')

        for raappt in expiring_ras:
            supervisor = raappt.hiring_faculty
            context = {'supervisor': supervisor, 'raappt': raappt}
            # Let's see if we have any Funding CC supervisors that should also get the reminder.
            cc = None
            fund_cc_roles = Role.objects_fresh.filter(unit=raappt.unit, role='FDCC')
            # If we do, let's add them to the CC list, but let's also make sure to use their role account email for
            # the given role type if it exists.
            if fund_cc_roles:
                people = []
                for role in fund_cc_roles:
                    people.append(role.person)
                people = list(set(people))
                cc = []
                for person in people:
                    cc.append(person.role_account_email('FDCC'))
            msg = EmailMultiAlternatives(subject, template.render(context), from_email, [supervisor.email()],
                                         headers={'X-coursys-topic': 'ra'}, cc=cc)
            msg.send()
            raappt.mark_reminded()

    def get_program_display(self):
        if self.program:
            return self.program.get_program_number_display()
        else:
            return '00000'

    def has_attachments(self):
        return self.attachments.visible().count() > 0


def ra_attachment_upload_to(instance, filename):
    return upload_path('raattachments', filename)

class RAAppointmentAttachmentQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)


class RAAppointmentAttachment(models.Model):
    """
    Like most of our contract-based objects, an attachment object that can be attached to them.
    """
    appointment = models.ForeignKey(RAAppointment, null=False, blank=False, related_name="attachments", on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('appointment',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=ra_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = RAAppointmentAttachmentQueryset.as_manager()

    def __str__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("appointment", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()


class SemesterConfig(models.Model):
    """
    A table for department-specific semester config.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    semester = models.ForeignKey(Semester, null=False, blank=False, on_delete=models.PROTECT)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
    defaults = {'start_date': None, 'end_date': None}
    # 'start_date': default first day of contracts that semester, 'YYYY-MM-DD'
    # 'end_date': default last day of contracts that semester, 'YYYY-MM-DD'
    
    class Meta:
        unique_together = (('unit', 'semester'),)
    
    @classmethod
    def get_config(cls, units, semester):
        """
        Either get existing SemesterConfig or return a new one.
        """
        configs = SemesterConfig.objects.filter(unit__in=units, semester=semester).select_related('semester')
        if configs:
            return configs[0]
        else:
            return SemesterConfig(unit=list(units)[0], semester=semester)
    
    def start_date(self):
        if 'start_date'in self.config:
            return datetime.datetime.strptime(self.config['start_date'], '%Y-%m-%d').date()
        else:
            return self.semester.start

    def end_date(self):
        if 'end_date'in self.config:
            return datetime.datetime.strptime(self.config['end_date'], '%Y-%m-%d').date()
        else:
            return self.semester.end

    def set_start_date(self, date):
        self.config['start_date'] = date.strftime('%Y-%m-%d')

    def set_end_date(self, date):
        self.config['end_date'] = date.strftime('%Y-%m-%d')

