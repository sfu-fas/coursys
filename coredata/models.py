from django.core.validators import RegexValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Count
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from django.conf import settings
import datetime, urllib.parse, decimal
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.mail import send_mail
from cache_utils.decorators import cached
from courselib.json_fields import JSONField
from courselib.json_fields import getter_setter, config_property
from courselib.conditional_save import ConditionalSaveMixin
from courselib.branding import product_name, help_email
from django.utils.safestring import mark_safe
from django.utils.html import escape
from bitfield import BitField
import fractions, itertools

def repo_name(offering, slug):
    """
    Label for a SVN repository
    """
    name = offering.subject.upper() + offering.number[0:3] + '-' + offering.semester.name + '-' + slug
    return name

VISA_STATUSES = ( # as taken from SIMS ps_visa_permit_tbl
        ('Perm Resid', 'Permanent Resident'),
        ('Student',    'Student Visa'),          # Student Authorization permitting study in Canada
        ('Diplomat',   'Diplomat'),              # Reciprocal domestic tuition may be extended to dependents of diplomats from certain countries (not all).
        ('Min Permit', "Minister's Permit"),
        ('Other',      'Other Visa'),
        ('Visitor',    "Visitor's Visa"),        # Does not permit long term study in Canada
        ('Unknown',    'Not Known'),
        ('New CDN',    "'New' Canadian citizen"),# Naturalized Canadian citizen whose SFU record previously showed another visa/permit status, such as Permanent Resident.
        ('Conv Refug', 'Convention Refugee'),
        ('Refugee',    'Refugee'),               # Refugee (status granted)
        ('Unknown',    'Non-Canadian, Status Unknown'), # Non-Canadian, Status Unknown (incl refugee claimants)
        ('No Visa St', 'Non-Canadian, No Visa Status'), # Non-Canadian, No Visa Status (student is studying outside Canada)
        ('Live-in Ca', 'Live-in Caregiver'),
        )

ROLE_CHOICES = (
        ('ADVS', 'Advisor'),
        ('ADVM', 'Advisor Manager'),
        ('FAC', 'Faculty Member'),
        ('SESS', 'Sessional Instructor'),
        ('COOP', 'Co-op Staff'),
        ('INST', 'Other Instructor'),
        ('SUPV', 'Additional Supervisor'),
        ('DISC', 'Discipline Case Administrator'),
        ('DICC', 'Discipline Case Filer (email CC)'),
        ('ADMN', 'Departmental Administrator'),
        ('TAAD', 'TA Administrator'),
        ('TADM', 'Teaching Administrator'),
        ('GRAD', 'Grad Student Administrator'),
        ('GRPD', 'Graduate Program Director'),
        ('FUND', 'Grad Funding Administrator'),
        ('FDRE', 'Grad Funding Requester'),
        ('FDCC', 'Grad Funding Reminder CC'),
        ('TECH', 'Tech Staff'),
        ('GPA', 'GPA conversion system admin'),
        ('OUTR', 'Outreach Administrator'),
        ('INV', 'Inventory Administrator'),
        ('FACR', 'Faculty Viewer'),
        ('REPV', 'Report Viewer'),
        ('FACA', 'Faculty Administrator'),
        ('RELA', 'Relationship Database User'),
        ('SPAC', 'Space Administrator'),
        ('FORM', 'Form Administrator'),
        ('SYSA', 'System Administrator'),
        ('NONE', 'none'),
        )
ROLES = dict(ROLE_CHOICES)
# roles departmental admins ('ADMN') are allowed to assign within their unit
UNIT_ROLES = ['ADVS', 'ADVM', 'TAAD', 'GRAD', 'FUND', 'FDRE', 'FDCC', 'GRPD',
              'SESS', 'COOP', 'INST', 'SUPV', 'OUTR', 'INV', 'FACR', 'FACA', 'RELA', 'SPAC', 'FORM']
# roles that give access to SIMS data
SIMS_ROLES = ['ADVS', 'ADMV', 'DISC', 'DICC', 'FUND', 'GRAD', 'GRPD']

# discipline-related roles.  We notify someone else on top of the DAs for those.
DISC_ROLES = ['DISC', 'DICC']

# help text for the departmental admin on those roles
ROLE_DESCR = {
        'ADVS': 'Has access to the advisor notes.',
        'ADVM': 'Can manage advisor visit categories.',
        'DISC': 'Can manage academic discipline cases in the unit: should include your Academic Integrity Coordinator.',
        'DICC': 'Will be copied on all discipline case letters in the unit: include whoever files your discipline cases.',
        'TAAD': 'Can administer TA job postings and appointments.',
        'TADM': 'Can manage teaching history for faculty members.',
        'GRAD': 'Can view and update the grad student database.',
        'GRPD': 'Director of the graduate program: typically the signer of grad-related letters.',
        'FUND': 'Can work with the grad student funding database.',
        'FDRE': 'Can submit grad student funding requests.',
        'FDCC': 'Gets copied on RA expiring reminder emails',
        'TECH': 'Can manage resources required for courses.',
        'FAC': 'Faculty Member',
        'SESS': 'Sessional Instructor',
        'COOP': 'Co-op Staff Member',
        'INST': 'Instructors outside of the department or others who teach courses',
        'REPV': 'Has Reporting Database Viewer Access.',
        'SUPV': 'Others who can supervise RAs or grad students, in addition to faculty',
        'OUTR': 'Can manage outreach events',
        'INV': 'Can manage assets',
        'FACR': 'Can view some faculty data (read-only)',
        'FACA': 'Can manage faculty data',
        'RELA': 'Can access relationship database',
        'SPAC': 'Can manage spaces',
        'FORM': 'Can manage form groups (and thus, forms)',
}
INSTR_ROLES = ["FAC", "SESS", "COOP", 'INST']  # roles that are given to categorize course instructors

# These are the gender values that are possible in SIMS. All other gender-handling should refer to this as a master
# list of values/descriptions.
GENDER_CHOICES = [
    ('M', 'male'),
    ('F', 'female'),
    ('X', 'non-binary'),
    ('U', 'prefer not to answer'),
]
GENDER_DESCR = dict(GENDER_CHOICES)


ROLE_MAX_EXPIRY = 730  # maximum days in the future a role can expire (except LONG_LIVED_ROLES roles)
LONG_LIVED_ROLES = ['FAC', 'SUPV'] # roles that don't allow access to anything, so may be longer lived


class Person(models.Model, ConditionalSaveMixin):
    """
    A person in the system (students, instuctors, etc.).
    """
    emplid = models.PositiveIntegerField(db_index=True, unique=True, null=False,
                                         verbose_name="ID #",
        help_text='Employee ID (i.e. student number)')
    userid = models.CharField(max_length=32, null=True, blank=True, db_index=True, unique=True, verbose_name="User ID",
        validators=[RegexValidator(regex=r'^[a-z0-9\-_]{2,12}$', message='userids can contain only letters and numbers')],
        help_text='SFU Unix userid (i.e. part of SFU email address before the "@").')
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField(max_length=32, null=True, blank=True)
    title = models.CharField(max_length=4, null=True, blank=True)
    temporary = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
        # 'email': email, if not the default userid@sfu.ca
        # 'pref_first_name': really, truly preferred first name (which can be set in DB if necessary)
        # 'phones': dictionary of phone number values. Possible keys: 'pref', 'home', 'cell', 'main'
        # 'addresses': dictionary of phone number values. Possible keys: 'home', 'mail'
        # 'gender': key from GENDER_CHOICES
        # 'citizen': country of citizenship (e.g. 'Canada')
        # 'visa': Canadian visa status (e.g. 'No visa st', 'Perm resid')
        # 'birthdate': birth date (e.g. '1980-12-31')
        # 'applic_email': application email address
        # 'gpa': Most recent CGPA for this student
        # 'ccredits': Number of completed credits
        # 'sin': Social Insurance Number (usually populated by TA/RA contracts)
        # 'nonstudent_hs': highschool field from NonStudent record
        # 'nonstudent_colg': college field from NonStudent record
        # 'nonstudent_notes': notes field from NonStudent record
        # 'phone_ext': local phone number (for faculty/staff) (e.g. '25555')
        # 'form_email': email address to be used by the onlineforms app for this person
        # 'external_email': external email for non-SFU grad committee members
        # '2fa': do we require this user to do 2FA for all logins?
        # 'recovery_email': non-SFU recovery email for 2FA: should be present if config['2fa'].

    defaults = {'email': None, 'gender': 'U', 'addresses': {}, 'gpa': 0.0, 'ccredits': 0.0, 'visa': None,
                'citizen': None, 'nonstudent_hs': '',  'nonstudent_colg': '', 'nonstudent_notes': None,
                'sin': '000000000', 'phone_ext': None, 'birthdate': None}
    _, set_email = getter_setter('email')
    _, set_pref_first_name = getter_setter('pref_first_name')
    gender, _ = getter_setter('gender')
    addresses, _ = getter_setter('addresses')
    gpa, _ = getter_setter('gpa')
    ccredits, _ = getter_setter('ccredits')
    # see VISA_STATUSES above for list of possibilities
    visa, _ = getter_setter('visa')
    citizen, _ = getter_setter('citizen')
    sin, set_sin = getter_setter('sin')
    phone_ext, set_phone_ext = getter_setter('phone_ext')
    nonstudent_hs, set_nonstudent_hs = getter_setter('nonstudent_hs')
    nonstudent_colg, set_nonstudent_colg = getter_setter('nonstudent_colg')
    nonstudent_notes, set_nonstudent_notes = getter_setter('nonstudent_notes')
    _, set_title = getter_setter('title')
    # Added for consistency with FuturePerson instead of manually having to probe the config
    birthdate, _ = getter_setter('birthdate')

    @staticmethod
    def emplid_header():
        return "ID Number"

    @staticmethod
    def userid_header():
        return "Userid"

    def __str__(self):
        return self.sortname()

    def name(self):
        return "%s %s" % (self.config.get('first_name', self.first_name), self.last_name)

    def sortname(self):
        return "%s, %s" % (self.last_name, self.config.get('first_name', self.first_name))

    def initials(self):
        return "%s%s" % (self.first_name[0], self.last_name[0])

    def full_email(self):
        return "%s <%s>" % (self.name_pref(), self.email())

    def real_pref_first(self):
        return self.config.get('pref_first_name', None) or self.pref_first_name or self.first_name

    def name_pref(self):
        return "%s %s" % (self.real_pref_first(), self.last_name)

    def first_with_pref(self):
        name = self.config.get('first_name', self.first_name)
        pref = self.real_pref_first()
        if pref != name:
            name += ' (%s)' % (pref)
        return name

    def sortname_pref(self):
        return "%s, %s" % (self.last_name, self.first_with_pref())

    def sortname_pref_only(self):
        return "%s, %s" % (self.last_name, self.real_pref_first())

    def name_with_pref(self):
        return "%s %s" % (self.first_with_pref(), self.last_name)

    def letter_name(self):
        if 'letter_name' in self.config:
            return self.config['letter_name']
        else:
            return self.name()

    def get_title(self):
        if 'title' in self.config:
            return self.config['title']
        elif self.title:
            return self.title
        elif 'gender' in self.config and self.config['gender'] == 'M':
            return 'Mr'
        elif 'gender' in self.config and self.config['gender'] == 'F':
            return 'Ms'
        else:
            return 'M'

    def email(self):
        if 'email' in self.config:
            return self.config['email']
        elif self.userid:
            return "%s@sfu.ca" % (self.userid)
        elif 'applic_email' in self.config:
            return self.config['applic_email']
        else:
            return None

    def userid_or_emplid(self):
        "userid if possible or emplid if not: inverse of find_userid_or_emplid searching"
        return self.userid or str(self.emplid)

    def get_gender_display(self):
        if 'gender' in self.config:
            return GENDER_DESCR.get(self.config['gender'], 'unknown')
        else:
            return 'unknown'

    def __lt__(self, other):
        return (self.last_name, self.first_with_pref(), self.userid_or_emplid()) < (other.last_name, other.first_with_pref(), other.userid_or_emplid())

    class Meta:
        verbose_name_plural = "People"
        ordering = ['last_name', 'first_name', 'userid']
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    
    def email_mailto(self):
        "A mailto: URL for this person's email address: handles the case where we don't know an email for them."
        email = self.email()
        if email:
            return mark_safe('<a href="mailto:%s">%s</a>' % (escape(email), escape(email)))
        else:
            return "None"

    def search_label_value(self):
        return "%s (%s), %s" % (self.name_with_pref(), self.userid, self.emplid)

    def get_role_account(self, type):
        """
        We're going to have to assume that a person has at most one role account.
        """
        ra = AnyPerson.objects.filter(person=self, role_account__isnull=False, role_account__type=type).first()
        if ra:
            return ra.role_account
        else:
            return None

    def role_account_email(self, type):
        ra = self.get_role_account(type)
        if ra:
            return "%s@sfu.ca" % ra.userid
        else:
            return self.email()

    def get_visas_summary(self):
        from visas.models import Visa
        visas = Visa.get_visas([self])
        return '; '.join("%s (%s)" % (v.status, v.get_validity()) for v in visas)

    @staticmethod
    def next_available_temp_emplid():
        p = Person.objects.filter(temporary=True).order_by('-emplid')
        if len(p) == 0:
            return 133700001
        else:
            return p[0].emplid + 1

    @staticmethod
    def next_available_temp_userid():
        return "tmp-"+str(Person.next_available_temp_emplid())[5:]


class FuturePersonManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)


class FuturePerson(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField(max_length=32, null=True, blank=True)
    title = models.CharField(max_length=4, null=True, blank=True)
    hidden = models.BooleanField(default=False, editable=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff

    defaults = {'email': None, 'birthdate': None, 'gender': 'U', 'sin': '000000000'}

    sin, set_sin = getter_setter('sin')
    email, set_email = getter_setter('email')
    gender, set_gender = getter_setter('gender')
    birthdate, set_birthdate = getter_setter('birthdate')
    # Something to mark if a FuturePerson's position has been assigned to a real Faculty Member
    _, set_assigned = getter_setter('assigned')

    objects = FuturePersonManager()

    def __str__(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)

    class Meta:
        verbose_name_plural = "FuturePeople"

    def hide(self):
        self.hidden = True

    def get_position_name(self):
        """
        Each FuturePerson should have at most one Position they are assigned to, and this will return that position's
        name, if it exists.
        """
        from faculty.models import Position

        # Each FuturePerson should be assigned to at most one AnyPerson...
        ap = AnyPerson.objects.filter(future_person=self).first()
        position = Position.objects.filter(any_person=ap).first()
        if position:
            return position.title or ''
        else:
            return ''

    def assigned(self):
        if self.config.get('assigned'):
            return True
        else:
            return False

    def is_anyperson(self):
        """
        Checks if there is at least one AnyPerson that has this object as a ForeignKey.
        Useful for the admin screens to know if we can safely delete it.

        :return: True or False
        :rtype: Boolean
        """

        return AnyPerson.objects.filter(future_person=self).count() > 0

    def delete(self):
        super(FuturePerson, self).delete()
        AnyPerson.delete_empty_anypersons()


class RoleAccount(models.Model):
    userid = models.CharField(max_length=8, db_index=True, verbose_name="User ID",
                              help_text='SFU Unix userid (i.e. part of SFU email address before the "@").')
    type = models.CharField(max_length=4, choices=ROLE_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff

    class Meta:
        unique_together = (('userid', 'type'),)

    def __str__(self):
        return "%s - %s" % (self.userid, self.type)

    def name(self):
        return self.__str__()


    def is_anyperson(self):
        """
        Checks if there is at least one AnyPerson that has this object as a ForeignKey.
        Useful for the admin screens to know if we can safely delete it.

        :return: True or False
        :rtype: Boolean
        """

        return AnyPerson.objects.filter(role_account=self).count() > 0

    def delete(self):
        super(RoleAccount, self).delete()
        AnyPerson.delete_empty_anypersons()


class AnyPerson(models.Model):
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True)
    future_person = models.ForeignKey(FuturePerson, on_delete=models.SET_NULL, null=True, blank=True)
    role_account = models.ForeignKey(RoleAccount, on_delete=models.SET_NULL, null=True, blank=True)

    def get_person(self):
        return self.person or self.role_account or self.future_person

    def __str__(self):
        if not self.get_person():
            return "None"
        return self.get_person().name()

    #  The following three methods to easily get attributes that are in Person and FuturePerson but not in RoleAccount.
    def last_name(self):
        try:
            return self.get_person().last_name
        except AttributeError:
            return None

    def first_name(self):
        try:
            return self.get_person().first_name
        except AttributeError:
            return None

    def middle_name(self):
        try:
            return self.get_person().middle_name
        except AttributeError:
            return None

    # Two more that only exist in Person objects.
    def userid(self):
        try:
            return self.get_person().userid
        except AttributeError:
            return None

    def emplid(self):
        try:
            return self.get_person().emplid
        except AttributeError:
            return None

    @classmethod
    def get_or_create_for(cls, person=None, role_account=None, future_person=None):
        """
        A method to either return (if one exists) or create an AnyPerson based on the possible
        parameters.  Only exactly one of these parameters should get passed in.  
        """
        if person:
            if role_account or future_person:
                raise ValidationError('More than one argument given.')
            if AnyPerson.objects.filter(person=person).exists():
                return AnyPerson.objects.filter(person=person)[0]
            else:
                anyperson = AnyPerson(person=person)
                anyperson.save()
                return anyperson
        elif role_account:
            if person or future_person:
                raise ValidationError('More than one argument given.')
            if AnyPerson.objects.filter(role_account=role_account).exists():
                return AnyPerson.objects.filter(role_account=role_account)[0]
            else:
                anyperson = AnyPerson(role_account=role_account)
                anyperson.save()
                return anyperson
        elif future_person:
            if person or role_account:
                raise ValidationError('More than one argument given.')
            if AnyPerson.objects.filter(future_person=future_person).exists():
                return AnyPerson.objects.filter(future_person=future_person)[0]
            else:
                anyperson = AnyPerson(future_person=future_person)
                anyperson.save()
                return anyperson
        else:
            raise ValidationError('You must supply exactly one of the three possible arguments')

    @classmethod
    def delete_empty_anypersons(cls):
        """
        When deleting FuturePersons/Role_Accounts, we may end up with AnyPersons that no longer have any foreign
        keys to any records at all.  This method deletes those to avoid cluttering the DB with empty records.  It gets
        called from either the RoleAccount or FuturePerson delete methods, and we also have a way to call it from the
        sysadmin AnyPersons management template.
        """
        count = 0
        for anyperson in AnyPerson.objects.all():
            if not anyperson.person and not anyperson.future_person and not anyperson.role_account:
                anyperson.delete()
                count += 1
        return count


class Semester(models.Model):
    """
    A semester object: not imported, must be created manually.
    """
    label_lookup = {
        '1': 'Spring',
        '4': 'Summer',
        '7': 'Fall',
        }
    slug_lookup = {
        '1': 'sp',
        '4': 'su',
        '7': 'fa',
        }
    months_lookup = {
        '1': 'Jan-Apr',
        '4': 'May-Aug',
        '7': 'Sep-Dec',
        }
    name = models.CharField(max_length=4, null=False, db_index=True, unique=True,
        help_text='Semester name should be in the form "1097".')
    start = models.DateField(help_text='First day of classes.')
    end = models.DateField(help_text='Last day of classes.')

    class Meta:
        ordering = ['name']
    def __lt__(self, other):
        return self.name < other.name
    def __le__(self, other):
        return self.name <= other.name
    def sem_number(self):
        "number of semesters since spring 1900 (for subtraction)"
        yr = int(self.name[0:3])
        sm = int(self.name[3])
        if sm == 1:
            return 3*yr + 0
        elif sm == 4:
            return 3*yr + 1
        elif sm == 7:
            return 3*yr + 2
        else:
            raise ValueError("Unknown semester number")
    def __sub__(self, other):
        "Number of semesters between the two args"
        return self.sem_number() - other.sem_number()

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    
    def label(self):
        """
        The human-readable label for the semester, e.g. "Summer 2010".
        """
        name = str(self.name)
        if len(name) < 3 or len(name) > 4:
            return "Invalid"
        if len(name) == 3:
            name = "0"+name
        if name[1] == '8':
            name = "0" + name[1:]
        year = 1900 + int(name[0:3])
        semester = self.label_lookup[name[3]]
        return semester + " " + str(year)
    def months(self):
        return self.months_lookup[self.name[3]]
    def slugform(self):
        """
        The slug version of the semester, e.g. "2010su".
        """
        name = str(self.name)
        year = 1900 + int(name[0:3])
        semester = self.slug_lookup[name[3]]
        return str(year) + semester

    def __str__(self):
        return self.label()
    
    def timely(self):
        """
        Is this semester temporally relevant (for display in menu)?
        """
        today = datetime.date.today()
        month_ago = today - datetime.timedelta(days=40)
        ten_days_ago = today + datetime.timedelta(days=10)
        return self.end > month_ago and self.start < ten_days_ago
    
    def week_weekday(self, dt, weeks=None):
        """
        Given a datetime, return the week-of-semester and day-of-week (with 0=Monday).
        """
        # gracefully deal with both date and datetime objects
        if isinstance(dt, datetime.datetime):
            date = dt.date()
        else:
            date = dt

        # find the "base": first known week before the given date
        if not weeks:
            weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.monday <= date:
                base = w
                break

        if base is None:
            ##raise ValueError, "Date seems to be before the start of semester."
            # might as well do something with the before-semester case.
            return 1,0

        diff = date - base.monday
        diff = int(round(diff.days + diff.seconds / 86400.0) + 0.5) # convert to number of days, rounding off any timezone stuff
        week = base.week + diff // 7
        wkday = date.weekday()
        return week, wkday
    
    def duedate(self, wk, wkday, time):
        """
        Calculate duedate based on week-of-semester and weekday.  Provided argument time can be either datetime.time or datetime.datetime: time is copied from this to new duedate.
        """
        # find the "base": first known week before wk
        weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.week <= wk:
                base = w
                break

        date = base.monday + datetime.timedelta(days=7 * (wk - base.week) + wkday)
        # construct the datetime from date and time.
        if time:
            dt = datetime.datetime(year=date.year, month=date.month, day=date.day,
                hour=time.hour, minute=time.minute, second=time.second,
                microsecond=time.microsecond, tzinfo=time.tzinfo)
        else:
            dt = datetime.date(year=date.year, month=date.month, day=date.day)
        return dt

    def previous_semester(self):
        "semester before this one"
        return self.offset(-1)
    def next_semester(self):
        "semester after this one"
        return self.offset(1)
    
    def offset(self, n):
        "The semester n semesters forward/back in time"
        if n > 0:
            try:
                return Semester.objects.filter(name__gt=self.name).order_by('name')[n-1]
            except IndexError:
                return None
        elif n < 0:
            try:
                return Semester.objects.filter(name__lt=self.name).order_by('-name')[(-n)-1]
            except IndexError:
                return None
        else:
            return self

    def offset_name(self, n):
        "as offset() but only calculate the semester.name, without querying the DB"
        OFFSET_LOOKUP = { # key: (current semester, sem offset), value: (year offset, new semester)
            (1, 0): (0, 1),
            (1, 1): (0, 4),
            (1, 2): (0, 7),
            (4, 0): (0, 4),
            (4, 1): (0, 7),
            (4, 2): (1, 1),
            (7, 0): (0, 7),
            (7, 1): (1, 1),
            (7, 2): (1, 4),
        }

        yrs, sems = divmod(n, 3)

        name = self.name
        year = 1900 + int(name[0:3])
        sem = int(name[3])

        yroff, newsem = OFFSET_LOOKUP[sem, sems]
        year += yrs + yroff

        return "%03i%s" % (year-1900, newsem)

    
    @classmethod
    def current(cls):
        return cls.get_semester()

    @staticmethod
    def start_end_dates(semester):
        """
        First and last days of the semester, in the way that financial people do (without regard to class start/end dates)
        """
        yr = int(semester.name[0:3]) + 1900
        sm = int(semester.name[3])
        if sm == 1:
            start = datetime.date(yr, 1, 1)
            end = datetime.date(yr, 4, 30)
        elif sm == 4:
            start = datetime.date(yr, 5, 1)
            end = datetime.date(yr, 8, 31)
        elif sm == 7:
            start = datetime.date(yr, 9, 1)
            end = datetime.date(yr, 12, 31)
        return start, end

    @classmethod
    def get_semester(cls, date=None):
        if not date:
            date = datetime.date.today()
        return Semester.objects.filter(start__lte=date).order_by('-start')[0]

    @classmethod
    def next_starting(cls):
        """
        The next semester that starts after now
        """
        today = datetime.date.today()
        sems = Semester.objects.filter(start__gt=today).order_by('start')
        if sems:
            return sems[0]
        else:
            # just in case there's nothing in the future
            sems = Semester.objects.order_by('-start')
            return sems[0]

    @classmethod
    def first_relevant(cls):
        """
        The first semester that's relevant for most reporting: first semester that ends after two months ago.
        """
        today = datetime.date.today()
        year = today.year
        if 1 <= today.month <= 2:
            # last fall semester
            year -= 1
            sem = 7
        elif 3 <= today.month <= 6:
            # this spring
            sem = 1
        elif 7 <= today.month <= 10:
            # this summer
            sem = 4
        elif 11 <= today.month <= 12:
            # this fall
            sem = 7
        
        name = "%03d%1d" % ((year - 1900), sem)
        return Semester.objects.get(name=name)

    @classmethod
    def range(cls, start, end):
        """
        Produce a list of semesters from start to end. 
        Semester.range( '1134', '1147' ) == [ '1134', '1137', '1141', '1144', '1147' ]

        Will run forever or fail if the end semester is not a valid semester. 
        """
        current_semester = Semester.objects.get(name=start)
        while current_semester and current_semester.name != end:
            yield str(current_semester.name)
            current_semester = current_semester.offset(1) 
        if current_semester:
            yield str(current_semester.name)

class SemesterWeek(models.Model):
    """
    Starting points for weeks in the semester.
    
    Every semester object needs at least a SemesterWeek for week 1.
    """
    semester = models.ForeignKey(Semester, null=False, on_delete=models.PROTECT)
    week = models.PositiveSmallIntegerField(null=False, help_text="Week of the semester (typically 1-13)")
    monday = models.DateField(help_text='Monday of this week.')
    
    def __str__(self):
        return "%s week %i" % (self.semester.name, self.week)
    class Meta:
        ordering = ['semester', 'week']
        unique_together = (('semester', 'week'))


HOLIDAY_TYPE_CHOICES = (
        ('FULL', 'Classes cancelled, offices closed'),
        ('CLAS', 'Classes cancelled, offices open'),
        ('OPEN', 'Classes as scheduled'),
        )

class Holiday(models.Model):
    """
    A holiday to display on the calendar (and possibly exclude classes on that day).
    """
    date = models.DateField(help_text='Date of the holiday', null=False, blank=False, db_index=True)
    semester = models.ForeignKey(Semester, null=False, on_delete=models.PROTECT)
    description = models.CharField(max_length=30, null=False, blank=False, help_text='Description of holiday, e.g. "Canada Day"')
    holiday_type = models.CharField(max_length=4, null=False, choices=HOLIDAY_TYPE_CHOICES,
        help_text='Type of holiday: how does it affect schedules?')
    def __str__(self):
        return "%s on %s" % (self.description, self.date)
    class Meta:
        ordering = ['date']


class Course(models.Model, ConditionalSaveMixin):
    """
    More abstract model for a course.
    
    Note that title (and possibly stuff in config) might change over time:
    values in CourseOffering should be used where available.
    """
    subject = models.CharField(max_length=8, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    title = models.CharField(max_length=30, help_text='The course title.')
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
    def autoslug(self):
        return make_slug(self.subject + '-' + self.number)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    
    class Meta:
        unique_together = (('subject', 'number'),)
        ordering = ('subject', 'number')
    def __str__(self):
        return "%s %s" % (self.subject, self.number)
    def __lt__(self, other):
        return (self.subject, self.number) < (other.subject, other.number)
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    def full_name(self):
        return "%s %s - %s" % (self.subject, self.number, self.title)


COMPONENT_CHOICES = (
        ('LEC', 'Lecture'),
        ('LAB', 'Lab'),
        ('TUT', 'Tutorial'),
        ('SEM', 'Seminar'),
        ('SEC', 'Section'), # "Section"?  ~= lecture?
        ('PRA', 'Practicum'),
        ('IND', 'Individual Work'),
        ('INS', 'INS'), # ???
        ('WKS', 'Workshop'),
        ('FLD', 'Field School'),
        ('STD', 'Studio'),
        ('OLC', 'OLC'), # ???
        ('RQL', 'RQL'), # ???
        ('RSC', 'RSC'), # ??? Showed up the first time 2017/05/18
        ('STL', 'STL'), # ???
        ('CNV', 'CNV'), # converted from SIMON?
        ('OPL', 'Open Lab'), # ???
        ('EXM', 'Exam'),  # First showed up 2017/09/20 with descr "PhD Oral Candidacy Exam"
        ('CAP', 'Capstone Required'),  # First showed up 2019/03/24.  go.sfu shows those classes as "Capstone Required"
        ('INT', 'Internship Required'),  # First encountered 2019/05/16.
        ('CAP', 'Capstone'),  # First showed up 2019/03/24.  go.sfu shows those classes as "Capstone Required"
        ('COP', 'Work Integrated Learning'),  # First encountered 2019/05/17.
        ('THE', 'Thesis Research'),  # First encountered 2019/05/17.
        ('PHC', 'Unknown'),  # First encountered 2021/03/09. Applied to grad transfer credits and not visible in go.sfu
        ('PHF', 'Placeholder'),  # First encountered 2021/03/11. Applied to grad placeholder enrolments and not visible in go.sfu
        ('CAN', 'Cancelled')
        )
COMPONENTS = dict(COMPONENT_CHOICES)
CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby Campus'),
        ('SURRY', 'Surrey Campus'),
        ('VANCR', 'Harbour Centre'),
        ('OFFST', 'Off-campus'),
        #('SEGAL', 'Segal Centre'),
        ('GNWC', 'Great Northern Way Campus'),
        #('KAM', 'Kamloops Campus'),
        ('METRO', 'Other Locations in Vancouver'),
        )
CAMPUS_CHOICES_SHORT = (
        ('BRNBY', 'Burnaby'),
        ('SURRY', 'Surrey'),
        ('VANCR', 'Harbour Ctr'),
        ('OFFST', 'Off-campus'),
        #('SEGAL', 'Segal Ctr'),
        ('GNWC', 'Great North. Way'),
        #('KAM', 'Kamloops'),
        ('METRO', 'Other Vancouver'),
        )
CAMPUSES = dict(CAMPUS_CHOICES)
CAMPUSES_SHORT = dict(CAMPUS_CHOICES_SHORT)
OFFERING_FLAGS = [
    ('write', 'W'),
    ('quant', 'Q'),
    ('bhum', 'B-Hum'),
    ('bsci', 'B-Sci'),
    ('bsoc', 'B-Soc'),
    ('combined', 'Combined section'), # used to flag sections that have been merged in the import
    ]
OFFERING_FLAG_KEYS = [flag[0] for flag in OFFERING_FLAGS]
WQB_FLAGS = [(k,v) for k,v in OFFERING_FLAGS if k != 'combined']
WQB_KEYS = [flag[0] for flag in WQB_FLAGS]
WQB_DICT = dict(WQB_FLAGS)
INSTR_MODE_CHOICES = [ # from ps_instruct_mode in reporting DB
    ('CO', 'Co-Op'),
    ('DE', 'Distance Education'),
    ('GI', 'Graduate Internship'),
    ('P', 'In Person'),
    ('PO', 'In Person - Off Campus'),
    ('PR', 'Practicum'),
    ('PF', 'In Person Field School'),
    ]
INSTR_MODE = dict(INSTR_MODE_CHOICES)


class CourseOffering(models.Model, ConditionalSaveMixin):
    subject = models.CharField(max_length=8, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN"')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1"')
    section = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Section should be in the form "C100" or "D100"')
    semester = models.ForeignKey(Semester, null=False, on_delete=models.PROTECT)
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES, db_index=True,
        help_text='Component of the offering, like "LEC" or "LAB"')
    instr_mode = models.CharField(max_length=2, null=False, choices=INSTR_MODE_CHOICES, default='P', db_index=True,
        help_text='The instructional mode of the offering')
    graded = models.BooleanField(default=True)
    owner = models.ForeignKey('Unit', null=True, help_text="Unit that controls this offering", on_delete=models.PROTECT)
    # need these to join in the SIMS database: don't care otherwise.
    crse_id = models.PositiveSmallIntegerField(null=True, db_index=True)
    class_nbr = models.PositiveIntegerField(null=True, db_index=True)

    title = models.CharField(max_length=30, help_text='The course title', db_index=True)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, db_index=True)
    enrl_cap = models.PositiveSmallIntegerField()
    enrl_tot = models.PositiveSmallIntegerField()
    wait_tot = models.PositiveSmallIntegerField()
    units = models.PositiveSmallIntegerField(null=True, help_text='The number of credits received by (most?) students in the course')
    course = models.ForeignKey(Course, null=False, on_delete=models.PROTECT)

    # WQB requirement flags
    flags = BitField(flags=OFFERING_FLAG_KEYS, default=0)
    
    members = models.ManyToManyField(Person, related_name="member", through="Member")
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
        # 'url': URL of course home page
        # 'department': department responsible for course (used by discipline module)
        # 'taemail': TAs' contact email (if not their personal email)
        # 'contact_url': URL used for TA contact (e.g. Slack chat)
        # 'labtut': are there lab sections? (default False)
        # 'labtas': TAs get the LAB_BONUS lab/tutorial bonus (default False)
        # 'labtut_use': the instructor cares about labs/tutorials and wants them displayed more
        # 'uses_svn': create SVN repos for this course? (default False)
        # 'indiv_svn': do instructors/TAs have access to student SVN repos? (default False)
        # 'instr_rw_svn': can instructors/TAs *write* to student SVN repos? (default False)
        # 'group_min': minimum group size
        # 'group_max': maximum group size
        # 'group_span_activities': are groups allowed to last for multiple activities?
        # 'extra_bu': number of TA base units required
        # 'page_creators': who is allowed to create new pages?
        # 'sessional_pay': amount the sessional was paid (used in grad finances)
        # 'joint_with': list of offerings this one is combined with (as CourseOffering.slug)
        # 'maillist': course mailing list (@sfu.ca). Used for CMPT in course homepage list
        # 'redirect_pages': If a Page has a migrated_to, should we redirect to the new location? Set by copy_course_setup.
        # 'discussion': uses the (old) discussion module

    defaults = {'taemail': None, 'url': None, 'labtut': False, 'labtas': False, 'indiv_svn': False,
                'uses_svn': False, 'extra_bu': '0', 'page_creators': 'STAF', 'discussion': False,
                'instr_rw_svn': False, 'joint_with': (), 'group_min': 1, 'group_max': 50,
                'maillist': None, 'labtut_use': False, 'group_span_activities': True,
                'contact_url': None}
    labtut, set_labtut = getter_setter('labtut')
    labtut_use, set_labtut_use = getter_setter('labtut_use')
    _, set_labtas = getter_setter('labtas')
    url, set_url = getter_setter('url')
    taemail, set_taemail = getter_setter('taemail')
    contact_url, set_contact_url = getter_setter('contact_url')
    indiv_svn, set_indiv_svn = getter_setter('indiv_svn')
    instr_rw_svn, set_instr_rw_svn = getter_setter('instr_rw_svn')
    extra_bu_str, set_extra_bu_str = getter_setter('extra_bu')
    page_creators, set_page_creators = getter_setter('page_creators')
    discussion, set_discussion = getter_setter('discussion')
    _, set_sessional_pay = getter_setter('sessional_pay')
    joint_with, set_joint_with = getter_setter('joint_with')
    _, set_group_min = getter_setter('group_min')
    _, set_group_max = getter_setter('group_max')
    group_span_activities, set_group_span_activities = getter_setter('group_span_activities')
    _, set_maillist = getter_setter('maillist')
    copy_config_fields = [ # fields that should be copied when instructor does "copy course setup"
            'url', 'taemail', 'indiv_svn', 'page_creators', 'discussion', 'uses_svn', 'instr_rw_svn',
            'group_min', 'group_max', 'group_span_activities', 'contact_url'
    ] 
    
    def autoslug(self):
        # changed slug format for fall 2011
        if self.semester.name >= "1117":
            if self.section[2:4] == "00":
                words = [str(s).lower() for s in (self.semester.slugform(), self.subject, self.number, self.section[:2])]
            else:
                # these shouldn't be in the DB anymore, but there are a few left, so handle them
                words = [str(s).lower() for s in (self.semester.slugform(), self.subject, self.number, self.section)]
        else:
            words = [str(s).lower() for s in (self.semester.name, self.subject, self.number, self.section)]
        return '-'.join(words)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    class Meta:
        ordering = ['-semester', 'subject', 'number', 'section']
        unique_together = (
            ('semester', 'subject', 'number', 'section'),
            ('semester', 'crse_id', 'section'),
            ('semester', 'class_nbr'))

    def __str__(self):
        return "%s %s %s (%s)" % (self.subject, self.number, self.section, self.semester.label())
    def name(self):
        if self.graded and self.section[2:4] == '00':
            return "%s %s %s" % (self.subject, self.number, self.section[:-2])
        else:
            return "%s %s %s" % (self.subject, self.number, self.section)
    
    def save(self, *args, **kwargs):
        # make sure CourseOfferings always have .course filled.
        if not self.course_id:
            self.set_course(save=False)
        super(CourseOffering, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('offering:course_info', kwargs={'course_slug': self.slug})
    
    def instructors(self):
        return (m.person for m in self.member_set.filter(role="INST").select_related('person'))

    def instructors_str(self):
        @cached(60*60*24*2)
        def _instr_str(pk):
            return '; '.join(p.sortname_pref() for p in CourseOffering.objects.get(pk=pk).instructors())
        return _instr_str(self.pk)

    def instructors_printing(self):
        # like .instructors() but honours the sched_print_instr flag
        return (m.person for m in self.member_set.filter(role="INST").select_related('person')
                if m.sched_print_instr())
    def instructors_printing_str(self):
        @cached(60*60*24*2)
        def _instr_printing_str(pk):
            return '; '.join(p.sortname_pref() for p in CourseOffering.objects.get(pk=pk).instructors_printing())
        return _instr_printing_str(self.pk)

    def tas(self):
        return (m.person for m in self.member_set.filter(role="TA"))
    def student_count(self):
        return self.members.filter(person__role='STUD').count()
    def combined(self):
        return self.flags.combined
    def set_combined(self, val):
        self.flags.combined = val

    def get_campus_display_(self):
        # override to handle the distance ed special case
        if self.instr_mode == 'DE':
            return 'Distance Education'
        if self.campus in CAMPUSES:
            return CAMPUSES[self.campus]
        else:
            return 'unknown'
    def get_campus_short_display(self):
        if self.instr_mode == 'DE':
            return 'Distance'
        if self.campus in CAMPUSES_SHORT:
            return CAMPUSES_SHORT[self.campus]
        else:
            return 'unknown'

    def get_mode_display(self):
        if self.section.startswith('B'):
            return 'Blended'
        else:
            return INSTR_MODE[self.instr_mode]

    def maillist(self):
        """
        The slug used in the CMPT course mailing list scheme
        """
        if 'maillist' in self.config and self.config['maillist']:
            return self.config['maillist']

        @cached(60*60*24*7)
        def _maillist(pk):
            o = CourseOffering.objects.get(pk=pk)
            num = o.number.replace('W', '')
            others = CourseOffering.objects \
                .filter(subject=o.subject, number__in=[num, num+'W'], semester_id=o.semester_id) \
                .exclude(pk=pk).exclude(component='CAN').exists()
            if others:
                return '%s-%s-%s' % (o.subject.lower(), num, o.section[0:2].lower())
            else:
                return '%s-%s' % (o.subject.lower(), num)

        return _maillist(self.pk)

    def group_min(self):
        if 'group_min' in self.config and self.config['group_min'] is not None:
            return self.config['group_min']
        else:
            return self.defaults['group_min']

    def group_max(self):
        if 'group_max' in self.config and self.config['group_max'] is not None:
            return self.config['group_max']
        else:
            return self.defaults['group_max']

    def get_wqb_display(self):
        flags = [WQB_DICT[f] for f,v in self.flags.items() if v and f in WQB_KEYS]
        if flags:
            return ', '.join(flags)
        else:
            return 'none'

    def extra_bu(self):
        return decimal.Decimal(self.extra_bu_str())
    def set_extra_bu(self, v):
        assert isinstance(v, decimal.Decimal)
        self.set_extra_bu_str(str(v))
    def labtas(self):
        """
        Handles the logic for LAB_BONUS base units.
        
        Default yes if there are lab/tutorial sections; default no otherwise. 
        """
        if 'labtas' in self.config:
            return self.config['labtas']
        elif 'labtut' in self.config and self.config['labtut']:
            return True
        else:
            return False
    def sessional_pay(self):
        """
        Pay for the sessional instructor: check self.owner for a value if not set on offering.
        """
        if 'sessional_pay' in self.config:
            return decimal.Decimal(self.config['sessional_pay'])
        elif 'sessional_pay' in self.owner.config:
            return decimal.Decimal(self.owner.config['sessional_pay'])
        else:
            return 0
    
    def set_course(self, save=True):
        """
        Set this objects .course field to a sensible value, creating a Course object if necessary.
        """
        cs = Course.objects.filter(subject=self.subject, number=self.number)
        if cs:
            self.course = cs[0]
        else:
            c = Course(subject=self.subject, number=self.number, title=self.title)
            c.save()
            self.course = c
        
        if save:
            self.save()
    
    def uses_svn(self):
        """
        Should students and groups in this course get Subversion repositories created?
        """
        return False
        #if 'uses_svn' in self.config and self.config['uses_svn']:
        #    return True
        #return self.subject == "CMPT" \
        #    and ((self.semester.name == "1117" and self.number in ["470", "379", "882"])
        #         or (self.semester.name >= "1121" and self.number >= "200"))

    def export_dict(self, instructors=None):
        """
        Produce dictionary of data about offering that can be serialized as JSON.

        May optionally pass as list of instructors (Member objects) if known, to save the query here.
        """
        if instructors is None:
            instructors = self.member_set.filter(role="INST").select_related('person')

        d = {}
        d['subject'] = self.subject
        d['number'] = self.number
        d['section'] = self.section
        d['semester'] = self.semester.name
        d['component'] = self.component
        d['title'] = self.title
        d['campus'] = self.campus
        d['meetingtimes'] = [m.export_dict() for m in self.meetingtime_set.all()]
        d['instructors'] = [{'userid': m.person.userid, 'name': m.person.name()} for m in instructors]
        d['wqb'] = [desc for flag,desc in WQB_FLAGS if getattr(self.flags, flag)]
        d['class_nbr'] = self.class_nbr
        return d
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")

    def __lt__(self, other):
        return (other.semester.name, self.subject, self.number, self.section) \
               < (self.semester.name, other.subject, other.number, other.section)
    def search_label_value(self):
        return "%s (%s)" % (self.name(), self.semester.label())


# https://stackoverflow.com/a/47817197/6871666
CourseOffering.get_campus_display = CourseOffering.get_campus_display_


class Member(models.Model, ConditionalSaveMixin):
    """
    "Members" of the course.  Role indicates instructor/student/TA/etc.

    Includes dropped students and non-graded sections (labs/tutorials).  Often want to select with:
        Member.objects.exclude(role="DROP").filter(...)
    """
    ROLE_CHOICES = (
        ('STUD', 'Student'),
        ('TA', 'TA'),
        ('INST', 'Instructor'),
        ('APPR', 'Grade Approver'),
        ('DROP', 'Dropped'),
        #('AUD', 'Audit Student'),
    )
    REASON_CHOICES = (
        ('AUTO', 'Automatically added'),
        ('TRU', 'TRU/OU Distance Student'),
        ('CTA', 'CourSys-Appointed TA'), # from ta app
        ('TAC', 'CourSys-Appointed TA'), # from tacontracts app
        ('TA', 'Additional TA'),
        ('TAIN', 'TA added by instructor'),
        ('INST', 'Additional Instructor'),
        ('UNK', 'Unknown/Other Reason'),
    )
    CAREER_CHOICES = (
        ('UGRD', 'Undergraduate'),
        ('GRAD', 'Graduate'),
        ('NONS', 'Non-Student'),
    )
    CAREERS = dict(CAREER_CHOICES)
    person = models.ForeignKey(Person, related_name="person", on_delete=models.PROTECT)
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    credits = models.PositiveSmallIntegerField(null=False, default=3,
        help_text='Number of credits this course is worth.')
    career = models.CharField(max_length=4, choices=CAREER_CHOICES)
    added_reason = models.CharField(max_length=4, choices=REASON_CHOICES, db_index=True)
    labtut_section = models.CharField(max_length=4, null=True, blank=True,
        help_text='Section should be in the form "C101" or "D103".')
    official_grade = models.CharField(max_length=2, null=True, blank=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # 'origsection': The originating section (for crosslisted sections combined here)
        #     represented as a CourseOffering.slug
        #     default: self.offering (if accessed by m.get_origsection())
        # 'bu': The number of BUs this TA has
        # 'teaching_credit': The number of teaching credits instructor receives for this offering. Fractions stored as strings: '1/3'
        # 'teaching_credit_reason': reason for the teaching credit override
        # 'last_discuss': Last view of the offering's discussion forum (seconds from epoch)
        # 'sched_print_instr': should this instructor be displayed in the course browser? ps_class_instr.sched_print_instr from SIMS
        # 'drop_date': for dropped students, the drop dates from SIMS (like '2000-12-31')

    defaults = {'bu': 0, 'teaching_credit': 1, 'teaching_credit_reason': None, 'last_discuss': 0,
                'sched_print_instr': True}
    raw_bu, set_bu = getter_setter('bu')
    last_discuss, set_last_discuss = getter_setter('last_discuss')
    sched_print_instr, set_sched_print_instr = getter_setter('sched_print_instr')
    
    def __str__(self):
        return "%s (%s) in %s" % (self.person.userid, self.person.emplid, self.offering,)
    def short_str(self):
        return "%s (%s)" % (self.person.name(), self.person.userid)
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    def clean(self):
        """
        Validate unique_together = (('person', 'offering', 'role'),) UNLESS role=='DROP'
        """
        if self.role == 'DROP':
            return
        if not hasattr(self, 'person'):
            raise ValidationError('No person set.')
        others = Member.objects.filter(person=self.person, offering=self.offering, role=self.role)
        if self.pk:
            others = others.exclude(pk=self.pk)

        if others:
            raise ValidationError('There is another membership with this person, offering, and role.  These must be unique for a membership (unless role is "dropped").')

    def bu(self):
        return decimal.Decimal(str(self.raw_bu()))

    @staticmethod
    def get_memberships(userid):
        """
        Get course memberships for this userid that we want to display on their menu. return list of Member objects and
        a boolean indicating whether or not there were temporal exclusions (so the "course history" link is relevant).
        """
        today = datetime.date.today()
        past1 = today - datetime.timedelta(days=365) # 1 year ago
        past2 = today - datetime.timedelta(days=730) # 2 years ago
        memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
                .filter(offering__graded=True, person__userid=userid) \
                .order_by('-offering__semester', 'offering') \
                .annotate(num_activities=Count('offering__activity')) \
                .annotate(num_pages=Count('offering__page')) \
                .select_related('offering','offering__semester')
        memberships = list(memberships) # get out of the database and do this locally

        # students don't see non-active courses or future courses
        memberships = [m for m in memberships if
                        m.role in ['TA', 'INST', 'APPR']
                        or ((m.num_activities > 0 or m.num_pages > 0)
                            and m.offering.semester.start <= today)]

        count1 = len(memberships)
        # exclude everything from more than 2 years ago
        memberships = [m for m in memberships if m.offering.semester.end >= past2]

        # students don't see as far in the past
        memberships = [m for m in memberships if
                        m.role in ['TA', 'INST', 'APPR']
                        or m.offering.semester.end >= past1]
        count2 = len(memberships)

        # exclude offerings explicity asked to not be in the students' menu by their .config
        memberships = [m for m in memberships if not (m.role == 'STUD' and 
                       'no_menu' in m.offering.config
                       and m.offering.config['no_menu'])]

        # have courses been excluded because of date?
        excluded = (count1-count2) != 0
        return memberships, excluded


    def teaching_credit(self):
        """
        Number of teaching credits this is worth, as a Fraction.
        """
        return self.teaching_credit_with_reason()[0]

    def teaching_credit_with_reason(self):
        """
        Number of teaching credits this is worth, as a Fraction, along with a short explanation for the value
        """
        assert self.role=='INST' and self.added_reason=='AUTO' # we can only sensibly calculate this for SIMS instructors

        if 'teaching_credit' in self.config:
            # if manually set, then honour it
            if 'teaching_credit_reason' in self.config:
                reason = self.config['teaching_credit_reason']
                if len(reason) > 15:
                    reason = 'set manually: ' + reason[:15] + '\u2026'
                else:
                    reason = 'set manually: ' + reason
            else:
                reason = 'set manually'
            return fractions.Fraction(self.config['teaching_credit']), reason
        elif self.offering.enrl_tot == 0:
            # no students => no teaching credit (probably a cancelled section we didn't catch on import)
            return fractions.Fraction(0), 'empty section'
        elif self.offering.instr_mode == 'DE':
            # No credit for distance-ed supervision
            return fractions.Fraction(0), 'distance ed'
        elif self.offering.instr_mode in ['CO', 'GI']:
            # No credit for co-op, grad-internship, distance-ed supervision
            return fractions.Fraction(0), 'co-op'
        elif MeetingTime.objects.filter(offering=self.offering, meeting_type__in=['LEC']).count() == 0:
            # no lectures probably means directed studies or similar
            return fractions.Fraction(0), 'no scheduled lectures'
        else:
            # now probably a real offering: split the credit among the (real SIMS) instructors and across joint offerings
            joint_with = CourseOffering.objects.filter(slug__in=self.offering.joint_with())
            other_instr = Member.objects.filter(offering=self.offering, role='INST', added_reason='AUTO').exclude(id=self.id)
            credits = fractions.Fraction(1)
            reasons = []
            if other_instr:
                other_instr = list(other_instr)
                credits /= len(other_instr) + 1
                reasons.append('co-taught with %s' % (', '.join(m.person.name() for m in other_instr)))
            if joint_with:
                joint_with = list(joint_with)
                credits /= len(joint_with) + 1
                reasons.append('joint with %s' % (', '.join(o.name() for o in joint_with)))
            #if self.offering.units is not None and self.offering.units != 3:
            #    # TODO: is this consistent with other units on campus? Do some have a different default credit count?
            #    credits *= fractions.Fraction(self.offering.units, 3)
            #    reasons.append('%i unit course' % (self.offering.units))
            return credits, '; '.join(reasons)

    def set_teaching_credit(self, cred):
        assert isinstance(cred, fractions.Fraction) or isinstance(cred, int)
        self.config['teaching_credit'] = str(cred)

    def set_teaching_credit_reason(self, reason):
        self.config['teaching_credit_reason'] = str(reason)

    def get_tug(self):
        assert self.role == 'TA'
        from ta.models import TUG

        tugs = TUG.objects.filter(member=self)
        if tugs:
            tug = tugs[0]
        else:
            tug = None
        return tug


    def svn_url(self):
        "SVN URL for this member (assuming offering.uses_svn())"
        return urllib.parse.urljoin(settings.SVN_URL_BASE, repo_name(self.offering, self.person.userid))

    def get_origsection(self):
        """
        The real CourseOffering for this student (for crosslisted sections combined in this system).
        """
        if 'origsection' in self.config:
            return CourseOffering.objects.get(slug=self.config['origsection'])
        else:
            return self.offering
    
    class Meta:
        #unique_together = (('person', 'offering', 'role'),)  # now handled by self.clean()
        ordering = ['offering', 'person']
    def get_absolute_url(self):
        return reverse('offering:student_info', kwargs={'course_slug': self.offering.slug,
                                                            'userid': self.person.userid_or_emplid()})
    
    @classmethod
    def clear_old_official_grades(cls):
        """
        Clear out the official grade field on old records: no need to tempt fate.
        """
        cutoff = datetime.date.today() - datetime.timedelta(days=120)
        old_grades = Member.objects.filter(offering__semester__end__lt=cutoff, official_grade__isnull=False)
        old_grades.update(official_grade=None)


WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
        )
WEEKDAYS = dict(WEEKDAY_CHOICES)
MEETINGTYPE_CHOICES = (
        ("LEC", "Lecture"),
        ("MIDT", "Midterm Exam"),
        ("EXAM", "Exam"),
        ("LAB", "Lab/Tutorial"),
        )
MEETINGTYPES = dict(MEETINGTYPE_CHOICES)


class MeetingTime(models.Model):
    offering = models.ForeignKey(CourseOffering, null=False, related_name='meeting_time', on_delete=models.PROTECT)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    start_day = models.DateField(null=False, help_text='Starting day of the meeting')
    end_day = models.DateField(null=False, help_text='Ending day of the meeting')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')
    exam = models.BooleanField(default=False) # unused: use meeting_type instead
    meeting_type = models.CharField(max_length=4, choices=MEETINGTYPE_CHOICES, default="LEC")
    labtut_section = models.CharField(max_length=4, null=True, blank=True,
        help_text='Section should be in the form "C101" or "D103".  None/blank for the non lab/tutorial events.')
    def __str__(self):
        return "%s %s %s-%s" % (str(self.offering), WEEKDAYS[self.weekday], self.start_time, self.end_time)

    class Meta:
        ordering = ['weekday']
        #unique_together = (('offering', 'weekday', 'start_time'), ('offering', 'weekday', 'end_time'))
    
    def export_dict(self):
        """
        Produce dictionary of data about meeting time that can be serialized as JSON
        """
        d = {}
        d['weekday'] = self.weekday
        d['start_day'] = str(self.start_day)
        d['end_day'] = str(self.end_day)
        d['start_time'] = str(self.start_time)
        d['end_time'] = str(self.end_time)
        d['room'] = self.room
        d['type'] = self.meeting_type
        return d

class Unit(models.Model):
    """
    An academic unit within the university: a department/school/faculty.
    
    Unit with label=='UNIV' is used for global roles
    """
    label = models.CharField(max_length=4, null=False, blank=False, db_index=True, unique=True,
            help_text="The unit code, e.g. 'CMPT'.")
    name = models.CharField(max_length=60, null=False, blank=False,
           help_text="The full name of the unit, e.g. 'School of Computing Science'.")
    parent = models.ForeignKey('Unit', null=True, blank=True, on_delete=models.PROTECT,
             help_text="Next unit up in the hierarchy.")
    acad_org = models.CharField(max_length=10, null=True, blank=True, db_index=True, unique=True, help_text="ACAD_ORG field from SIMS")
    def autoslug(self):
        return self.label.lower()
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # 'address': list of (3) lines in mailing address (default: SFU main address)
        # 'email': contact email address (may be None)
        # 'web': URL
        # 'tel': contact phone number
        # 'fax': fax number (may be None)
        # 'deptid': department ID for finances
        # 'informal_name': formal name of the unit (e.g. "Computing Science")
        # 'sessional_pay': default amount sessionals are paid (used in grad finances)
        # 'card_account':  Account code for card access forms
        # 'card_rooms': Rooms all grads have access to; separate lines with "|" and buildings/rooms with ":", e.g. "AQ:1234|AQ:5678"
    
    defaults = {'address': ['8888 University Drive', 'Burnaby, BC', 'Canada V5A 1S6'],
                'email': None, 'tel': '778.782.3111', 'fax': None, 'web': 'http://www.sfu.ca/',
                'deptid': ''}
    address, set_address = getter_setter('address')
    email, set_email = getter_setter('email')
    tel, set_tel = getter_setter('tel')
    fax, set_fax = getter_setter('fax')
    web, set_web = getter_setter('web')
    deptid, set_deptid = getter_setter('deptid')
    _, set_informal_name = getter_setter('informal_name')

    class Meta:
        ordering = ['label']

    def __str__(self):
        return "%s (%s)" % (self.name, self.label)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    
    def informal_name(self):
        if 'informal_name' in self.config and self.config['informal_name']:
            return self.config['informal_name']
        else:
            return self.name
    
    def uses_fasnet(self):
        """
        Used to decide whether or not to display the FASnet account forms.
        """
        return self.slug in ['cmpt', 'ensc']
    
    @classmethod
    #@cached(24*3600)
    def __sub_unit_ids(cls, unitids):
        """
        Do the actual work for sub_unit_ids
        """
        children = unitids
        decendants = set(children)
        while True:
            children = Unit.objects.filter(parent__in=children).values('id')
            children = set(u['id'] for u in children)
            if not children:
                break
            decendants |= children
        return decendants

    @classmethod
    def sub_unit_ids(cls, units, by_id=False):
        """
        Get the Unit.id values for all descendants of the given list of unit.id values.

        Cached so we can avoid the work when possible.
        """
        # sort unit.id values for consistent cache keys
        if by_id:
            unitids = sorted(list(set(units)))
        else:
            unitids = sorted(list(set(u.id for u in units)))
        return Unit.__sub_unit_ids(unitids)

    @classmethod
    def sub_units(cls, units, by_id=False):
        ids = cls.sub_unit_ids(units, by_id=by_id)
        return Unit.objects.filter(id__in=ids)

    def __super_units(self):
        if not self.parent:
            return []
        else:
            return [self.parent] + self.parent.super_units()
            
    def super_units(self, include_self=False):
        """
        Units directly above this in the heirarchy
        """
        key = 'superunits-' + self.slug
        res = cache.get(key)
        if res:
            if include_self:
                return res + [self]
            else:
                return res
        else:
            res = self.__super_units()
            cache.set(key, res, 24*3600)
            if include_self:
                return res + [self]
            else:
                return res


class Role(models.Model):
    """
    Additional roles within the system (not course-related).
    """
    class RoleNonExpiredManager(models.Manager):
        def get_queryset(self):
            return super(Role.RoleNonExpiredManager, self).get_queryset().filter(expiry__gte=datetime.date.today())

    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    expiry = models.DateField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # 'gone': used with role='FAC' to indicate this person has left/retired/whatever
        # 'giver': userid of the user who assigned the role
        # 'given_date': date the role was assigned

    gone = config_property('gone', False)

    objects = models.Manager()
    objects_fresh = RoleNonExpiredManager()

    def __str__(self):
        return "%s (%s, %s)" % (self.person, ROLES[str(self.role)], self.unit.label)
    class Meta:
        unique_together = (('person', 'role', 'unit'),)

    @classmethod
    def all_roles(cls, userid):
        return set((r.role for r in Role.objects_fresh.filter(person__userid=userid)))

    def expires_far(self):
        return self.expiry - datetime.date.today() < datetime.timedelta(days=182)

    def expires_soon(self):
        return self.expiry - datetime.date.today() < datetime.timedelta(days=14)

    @staticmethod
    def expiring_warning_email(recipients, roles, url, cc=[]):
        """
        Send one expiry warning email
        """
        from django.core.mail.message import EmailMessage
        expiring_list = '\n'.join(
            '  - %s as a %s in %s on %s.' % (r.person.name(), r.get_role_display(), r.unit.name, r.expiry)
            for r in roles
        )
        message = 'The following administrative roles within %s are expiring soon:\n\n%s\n\n' \
                  'If these roles are still appropriate, please renew them soon by visiting this page: %s\n\n' \
                  'This might be a good time to see if any other roles need to be revoked as well.\n' \
                  'Thanks, your friendly automated reminder.' % (product_name(hint='admin'), expiring_list, url)

        mail = EmailMessage(
            subject=product_name(hint='admin') + ' roles expiring',
            body=message,
            from_email=help_email(hint='admin'),
            to=recipients,
            cc=cc,
        )
        mail.send()

    @staticmethod
    def warn_expiring():
        """
        Email appropriate admins about soon-to-expire Roles
        """
        today = datetime.date.today()
        cutoff = datetime.date.today() + datetime.timedelta(days=14)

        expiring_roles = Role.objects.filter(expiry__gte=today, expiry__lte=cutoff).exclude(role__in=LONG_LIVED_ROLES)\
            .select_related('person', 'unit')
        unit_roles = {} # who do we remind about what?
        global_roles = []
        discipline_roles = []

        for r in expiring_roles:
            if r.unit.slug != 'univ' and r.role in UNIT_ROLES:
                unit_roles[r.unit] = unit_roles.get(r.unit, [])
                unit_roles[r.unit].append(r)
            elif r.unit.slug != 'univ' and r.role in DISC_ROLES:
                discipline_roles.append(r)
            else:
                global_roles.append(r)

        for unit, roles in list(unit_roles.items()):
            recipients = [r.person.full_email()
                          for r in Role.objects_fresh.filter(role='ADMN', unit=unit).select_related('person')]
            url = settings.BASE_ABS_URL + reverse('admin:unit_role_list')
            Role.expiring_warning_email(recipients, roles, url)

        if global_roles:
            recipients = [r.person.full_email()
                          for r in Role.objects_fresh.filter(role='SYSA', unit__slug='univ').select_related('person')]
            url = settings.BASE_ABS_URL + reverse('sysadmin:role_list')
            Role.expiring_warning_email(recipients, global_roles, url)

        if discipline_roles:
            recipients = [r.person.full_email()
                          for r in Role.objects_fresh.filter(role='DISC', unit__slug='univ').select_related('person')]
            url = settings.BASE_ABS_URL + reverse('discipline:permission_admin')
            Role.expiring_warning_email(recipients, discipline_roles, url)

    @staticmethod
    def purge_expired():
        """
        In theory, all of the code that uses Roles should be checking the .expiry date. This purges expired roles, just
        to be sure.
        """
        from log.models import LogEntry
        today = datetime.date.today()
        expired_roles = Role.objects.filter(expiry__lte=today).exclude(role__in=LONG_LIVED_ROLES).select_related('person')
        for r in expired_roles:
            l = LogEntry(userid='sysadmin',
                         description=("automatically purged expired role %s for %s") % (
                             r.role, r.person.userid),
                         related_object=r.person)
            l.save()
            r.delete()


class CombinedOffering(models.Model):
    """
    A model to represent a local fake CourseOffering that should be the result of combining members of two or more
    CourseOffering objects on import.
    """
    subject = models.CharField(max_length=4, null=False, blank=False)
    number = models.CharField(max_length=4, null=False, blank=False)
    section = models.CharField(max_length=4, null=False, blank=False)
    semester = models.ForeignKey(Semester, null=False, blank=False, on_delete=models.PROTECT)
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES)
    instr_mode = models.CharField(max_length=2, null=False, choices=INSTR_MODE_CHOICES, default='P')
    owner = models.ForeignKey('Unit', null=True, help_text="Unit that controls this offering", on_delete=models.PROTECT)
    crse_id = models.PositiveSmallIntegerField(null=True)
    class_nbr = models.PositiveIntegerField(null=True) # fake value for DB constraint on CourseOffering

    title = models.CharField(max_length=30)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES)

    offerings = models.ManyToManyField(CourseOffering)
        # actually a Many-to-One, but don't want to junk CourseOffering up with another ForeignKey

    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff

    def name(self):
        return "%s %s %s" % (self.subject, self.number, self.section)

    def create_combined_offering(self):
        """
        Do the import-like work of creating/updating the CourseOffering object
        """
        with transaction.atomic():
            try:
                offering = CourseOffering.objects.get(semester=self.semester, subject=self.subject,
                        number=self.number, section=self.section)
            except CourseOffering.DoesNotExist:
                offering = CourseOffering(semester=self.semester, subject=self.subject,
                        number=self.number, section=self.section)
                offering.enrl_cap = 0
                offering.enrl_tot = 0
                offering.wait_tot = 0
                offering.set_combined(True)
                offering.save()

            offering.component = self.component
            offering.instr_mode = self.instr_mode
            offering.owner = self.owner
            offering.crse_id = self.crse_id
            offering.class_nbr = self.class_nbr
            offering.title = self.title
            offering.campus = self.campus

            cap_total = 0
            tot_total = 0
            wait_total = 0
            labtut = False
            in_section = set() # students who are in section and not dropped (so we don't overwrite with a dropped membership)
            for sub in self.offerings.all():
                cap_total += sub.enrl_cap
                tot_total += sub.enrl_tot
                wait_total += sub.wait_tot
                labtut = labtut or sub.labtut()
                for m in sub.member_set.all():
                    old_ms = offering.member_set.filter(offering=offering, person=m.person)
                    if old_ms:
                        # was already a member: update.
                        old_m = old_ms[0]
                        old_m.role = m.role
                        old_m.credits = m.credits
                        old_m.career = m.career
                        old_m.added_reason = m.added_reason
                        old_m.config['origsection'] = sub.slug
                        old_m.labtut_section = m.labtut_section
                        if m.role != 'DROP' or old_m.person_id not in in_section:
                            # condition keeps from overwriting enrolled students with drops (from other section)
                            old_m.save()
                        if m.role != 'DROP':
                            in_section.add(old_m.person_id)
                    else:
                        # new membership: duplicate into combined
                        new_m = Member(offering=offering, person=m.person, role=m.role, labtut_section=m.labtut_section,
                                credits=m.credits, career=m.career, added_reason=m.added_reason)
                        new_m.config['origsection'] = sub.slug
                        new_m.save()
                        if m.role != 'DROP':
                            in_section.add(new_m.person_id)

            offering.enrl_cap = cap_total
            offering.enrl_tot = tot_total
            offering.wait_tot = wait_total
            offering.set_labtut(labtut)
            offering.save()


class EnrolmentHistory(models.Model):
    """
    A model to store daily history of course enrolments, since that isn't kept in SIMS.
    """
    offering = models.ForeignKey(CourseOffering, null=False, blank=False, on_delete=models.PROTECT)
    date = models.DateField()
    enrl_cap = models.PositiveSmallIntegerField()
    enrl_tot = models.PositiveSmallIntegerField()
    wait_tot = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = (('offering', 'date'),)

    def __str__(self):
        return '%s@%s (%i, %i, %i)' % (self.offering.slug, self.date, self.enrl_cap, self.enrl_tot, self.wait_tot)

    @classmethod
    def from_offering(cls, offering, date=None, save=True):
        """
        Build an EnrolmentHistory for this offering (today or on given date).
        """
        eh = cls(offering=offering)
        eh.enrl_cap = offering.enrl_cap
        eh.enrl_tot = offering.enrl_tot
        eh.wait_tot = offering.wait_tot

        if date:
            eh.date = date
        else:
            eh.date = datetime.date.today()

        if save:
            eh.save_or_replace()

    @property
    def enrl_vals(self):
        return self.enrl_cap, self.enrl_tot, self.wait_tot

    def is_dup(self, other):
        "Close enough that other can be deleted?"
        assert self.date < other.date
        return self.enrl_vals == other.enrl_vals

    @classmethod
    def deduplicate(cls, start_date=None, end_date=None, dry_run=False):
        """
        Remove any EnrolmentHistory objects that aren't adding any new information.
        """
        all_ehs = EnrolmentHistory.objects.order_by('offering', 'date')
        if start_date:
            all_ehs = all_ehs.filter(date__gte=start_date)
        if end_date:
            all_ehs = all_ehs.filter(date__lte=end_date)

        for off_id, ehs in itertools.groupby(all_ehs, key=lambda eh: eh.offering_id):
            # iterate through EnrolmentHistory for this offering and purge any "same as yesterday" entries
            with transaction.atomic():
                current = next(ehs)
                for eh in ehs:
                    if current.is_dup(eh):
                        if not dry_run:
                            eh.delete()
                        else:
                            print('delete', eh)
                    else:
                        current = eh

    def save_or_replace(self):
        """
        Save this object, or replace an existing one if the unique_together constraint fails.
        """
        try:
            with transaction.atomic():
                self.save()
        except IntegrityError:
            other = EnrolmentHistory.objects.get(offering=self.offering, date=self.date)
            other.enrl_cap = self.enrl_cap
            other.enrl_tot = self.enrl_tot
            other.wait_tot = self.wait_tot
            other.save()
