from django import forms
from django.conf import settings
from coredata.models import Role, Person, Member, Course, CourseOffering, Unit, Semester, SemesterWeek, Holiday, \
    CombinedOffering, AnyPerson, FuturePerson, RoleAccount, ROLE_MAX_EXPIRY, SIMS_ROLES
from coredata.queries import find_person, add_person, SIMSProblem, userid_to_emplid
from cache_utils.decorators import cached
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from coredata.widgets import CalendarWidget


# deprecated code from django-localflavor: https://github.com/django/django-localflavor/blob/1.4.x/localflavor/ca/forms.py
import re
from django.core.validators import EMPTY_VALUES
phone_digits_re = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')
class CAPhoneNumberField(forms.Field):
    """Canadian phone number form field."""

    default_error_messages = {
        'invalid': 'Phone numbers must be in XXX-XXX-XXXX format.',
    }

    def clean(self, value):
        super(CAPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        value = re.sub(r'(\(|\)|\s+)', '', force_text(value))
        m = phone_digits_re.search(value)
        if m:
            return '%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise forms.ValidationError(self.error_messages['invalid'])


class OfferingSelect(forms.TextInput):
    pass


class OfferingField(forms.ModelChoiceField):
    """
    Override ModelChoiceField so we don't have to build CourseOffering.objects.all()
    unnecessarily, and can set other parameters appropriately.
    """
    def __init__(self, *args, **kwargs):
        if 'help_text' in kwargs:
            help_text = kwargs['help_text']
            del kwargs['help_text']
        else:
            help_text = "Type to search for course offerings."
        super(OfferingField, self).__init__(*args, queryset=CourseOffering.objects.none(), widget=OfferingSelect(attrs={'size': 30}), help_text=help_text, **kwargs)
        
    def to_python(self, value):
        if not self.required and not value:
            return None
        try:
            co = CourseOffering.objects.exclude(component="CAN").get(pk=value, graded=True)
        except (ValueError, CourseOffering.DoesNotExist):
            raise forms.ValidationError("Unknown course offering selectted")
        return co


class CourseField(forms.ModelChoiceField):
    """
    Override ModelChoiceField so we don't have to build Course.objects.all()
    unnecessarily, and can set other parameters appropriately.
    """
    def __init__(self, *args, **kwargs):
        super(CourseField, self).__init__(*args, queryset=Course.objects.none(), widget=OfferingSelect(attrs={'size': 30}), help_text="Type to search for course offerings.", **kwargs)
        
    def to_python(self, value):
        try:
            co = Course.objects.get(pk=value)
        except (ValueError, Course.DoesNotExist):
            raise forms.ValidationError("Unknown course offering selectted")
        return co


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        exclude = ('config',)
        widgets = {
                   'label': forms.TextInput(attrs={'size': 5, 'autofocus': True}),
                   'name': forms.TextInput(attrs={'size': 40}),
                   'acad_org': forms.TextInput(attrs={'size': 10}),
                   }

    # from http://stackoverflow.com/a/1400046/1236542
    def clean_acad_org(self):
        acad_org = self.cleaned_data['acad_org']
        if acad_org == '':
            acad_org = None
        return acad_org


class PersonForm(forms.ModelForm):
    emplid = forms.CharField(max_length=9,
                    help_text='Employee ID (i.e. student number).  Enter a number starting with "0000" if unknown: will be filled in based on userid at next import',
                    widget=forms.TextInput(attrs={'size':'9','autofocus': True}))
    email = forms.CharField(max_length=50, required=False,
                    help_text='Person\'s email address (if not userid@sfu.ca)',
                    widget=forms.TextInput(attrs={'size':'20'}))
    class Meta:
        model = Person
        exclude = ['config']
    
    def clean_email(self):
        """
        Get the email address into the config, where it belongs
        """
        email = self.cleaned_data['email']
        if email:
            self.instance.set_email(email)
        return email

class EditPersonForm(forms.ModelForm):
    pref_first_name = forms.CharField(max_length=32, required=False,
                                      label="Preferred First Name", widget=forms.TextInput(attrs={'size':'20'}))
    email = forms.CharField(max_length=50, required=False,
                            help_text='Person\'s email address (if not userid@sfu.ca)',
                            widget=forms.TextInput(attrs={'size':'20'}))

    class Meta:
        model = Person
        fields = ()

    def clean_email(self):
        """
        Get the email address into the config, where it belongs
        """
        email = self.cleaned_data['email']
        if email:
            self.instance.set_email(email)
        elif 'email' in self.instance.config:
            del self.instance.config['email']
        return email

    def clean_pref_first_name(self):
        """
        Get the preferred first name into the config
        """
        pref_first_name = self.cleaned_data['pref_first_name']
        if pref_first_name:
            self.instance.set_pref_first_name(pref_first_name)
        elif 'pref_first_name' in self.instance.config:
            del self.instance.config['pref_first_name']
        return pref_first_name

class PersonWidget(forms.TextInput):
    """
    A widget to allow selecting a person by emplid, where they might not be in the coredata.Person table yet
    """
    def __init__(self, *args, **kwargs):
        self.found_sims = False
        super(PersonWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if self.found_sims:
            textwidget = super(PersonWidget, self).render(name, value, attrs)
            confirmwidget = ' Import %s %s (%s) from SIMS: ' % (self.sims_data['first_name'], self.sims_data['last_name'], self.sims_data['emplid'])
            confirmwidget += '<input type="checkbox" name="%s_confirm" />' % (name)
            confirmwidget += '<input type="hidden" name="%s_emplid" value="%s" />' % (name, self.sims_data['emplid'])
            return textwidget + confirmwidget
        else:
            return super(PersonWidget, self).render(name, value, attrs=attrs, renderer=renderer)


class PersonField(forms.CharField):
    """
    A field to allow emplid entry of a Person, but will find new people from SIMS if they aren't
    already a coredata.Person.

    If using, must override is_valid in your form as:
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(MyFormClass, self).is_valid(*args, **kwargs)
    
    You might also want to autocomplete for people in the system:
    $(document).ready(function() {
      ...
      $('#id_person').each(function() {
        $(this).autocomplete({
          source: '/data/students',
          minLength: 2,
          select: function(event, ui){
            $(this).data("val", ui.item.value);
          }
        });
      });
      ...
    });  
    """
    def __init__(self, *args, **kwargs):
        widget = PersonWidget()
        kwargs['widget'] = widget
        self.needs_email = kwargs.pop('needs_email', False)
        return super(PersonField, self).__init__(*args, **kwargs)

    def __check_email(self, p):
        """
        Check that the about-to-be-returned person has a valid email address (if relevant)
        """
        if not self.needs_email:
            return p

        if not p.userid and 'email' not in p.config:
            raise forms.ValidationError("No email address is known for this person: we need an email here.")

        return p
    

    def clean(self, value):
        if isinstance(value, Person):
            return self.__check_email(value)
        else:
            if not self.required and not value:
                return None

            try:
                return self.__check_email(Person.objects.get(emplid=value))
            except (ValueError, Person.DoesNotExist):
                # try to find the emplid in SIMS if they are missing from our DB
                if not value:
                    raise forms.ValidationError("Could not find this emplid.")

                if not value.isdigit(): # doesn't look like an emplid: try it as a userid
                    try:
                        return self.__check_email(Person.objects.get(userid=value))
                    except Person.DoesNotExist:
                        value = userid_to_emplid(value)
                        if not value:
                            raise forms.ValidationError("Could not find this emplid.")

                try:
                    persondata = find_person(value)
                except SIMSProblem as e:
                    raise forms.ValidationError("Problem locating person in SIMS: " + str(e))
                if not persondata:
                    raise forms.ValidationError("Could not find this emplid.")
                
                # we found this emplid in SIMS: raise validation error, but offer to add next time.
                confirm = self.fieldname+'_confirm'
                checkemplid = self.fieldname+'_emplid'
                if confirm in self.formdata and checkemplid in self.formdata and self.formdata[checkemplid] == value:
                    # new person was presented in the form last time, and they confirmed import
                    p = add_person(value)
                    return self.__check_email(p)
                else:
                    self.widget.found_sims = True
                    self.widget.sims_data = persondata
                    raise forms.ValidationError("Person is new to this system: please confirm their import.")
    
    @classmethod
    def person_data_prep(cls, form):
        for name, personfield in [(f, form.fields[f]) for f in form.fields if isinstance(form.fields[f], PersonField)]:
            personfield.formdata = form.data
            personfield.fieldname = name
    
    def prepare_value(self, value):
        if isinstance(value, Person):
            return value.emplid
        else:
            return value

class SysAdminSearchForm(forms.Form):
    user = PersonField(required=False)
    offering = OfferingField(required=False)

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(SysAdminSearchForm, self).is_valid(*args, **kwargs)
    def __init__(self, *args, **kwargs):
        super(SysAdminSearchForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget.attrs.update({'autofocus': 'autofocus'})
        
class MemberForm(forms.ModelForm):
    person = PersonField()
    offering = OfferingField()
    
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(MemberForm, self).is_valid(*args, **kwargs)
    
    class Meta:
        model = Member
        exclude = ('config', 'official_grade')
    
class OneOfferingForm(forms.Form):
    offering = OfferingField(help_text='Offering to combine')

class NewCombinedForm(forms.ModelForm):
    class Meta:
        model = CombinedOffering
        exclude = ('semester', 'crse_id', 'class_nbr', 'config', 'offerings')
    def __init__(self, *args, **kwargs):
        super(NewCombinedForm, self).__init__(*args, **kwargs)
        self.fields['subject'].widget.attrs.update({'autofocus': 'autofocus'})

class RoleForm(forms.ModelForm):
    person = PersonField(label="Emplid", help_text="or type to search")

    class Meta:
        model = Role
        exclude = ['config']
        widgets = {
            'expiry': CalendarWidget
        }

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RoleForm, self).is_valid(*args, **kwargs)

    def clean(self, fromunit=False):
        #  Allow sysadmins to assign roles that DAs should assign, but only for the University-wide level.
        cleaned_data = super(RoleForm, self).clean()
        role = cleaned_data.get('role')
        unit = cleaned_data.get('unit')
        person = cleaned_data.get('person')
        if not fromunit and role in SIMS_ROLES and unit.slug != 'univ':
            url = reverse('admin:unit_admin')
            raise forms.ValidationError({'role': 'Admins cannot assign that role. It must be given by their manager '
                                                 'at %s%s' % (settings.BASE_ABS_URL, url)})
        if Role.objects_fresh.filter(person=person, role=role, unit=unit).exists():
            raise forms.ValidationError({'role': 'This user already has that role for that unit.',
                                         'person': 'This user already has that role for that unit.',
                                         'unit': 'This user already has that role for that unit.'})

    def clean_expiry(self):
        expiry = self.cleaned_data['expiry']
        today = datetime.date.today()
        if expiry < today:
            raise forms.ValidationError('Role cannot expire in the past.')
        if expiry > today + datetime.timedelta(days=ROLE_MAX_EXPIRY):
            raise forms.ValidationError('Role cannot expire more than %i days in the future.' % (ROLE_MAX_EXPIRY,))
        return expiry


class UnitRoleForm(RoleForm):
    role = forms.ChoiceField(widget=forms.RadioSelect())

    def clean(self):
        return super(UnitRoleForm, self).clean(fromunit=True)


class OffboardForm(forms.Form):
    person = PersonField(label="Emplid", help_text="or type to search")
    delete_roles = forms.BooleanField(required=False, help_text="Check this box to remove all roles for this user in "
                                                                "your unit(s).")
    delete_formgroups = forms.BooleanField(required=False, help_text="Check this box to remove this user from all "
                                                                     "formgroups in your unit(s).")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(OffboardForm, self).is_valid(*args, **kwargs)

    def clean(self):
        cleaned_data = super(OffboardForm, self).clean()
        delete_roles = cleaned_data.get('delete_roles')
        delete_formgroups = cleaned_data.get('delete_formgroups')
        if not delete_roles and not delete_formgroups:
            raise forms.ValidationError({'delete_roles': 'You must select at least one of these options.',
                                         'delete_formgroups': 'You must select at least one of these options.'})


class InstrRoleForm(forms.Form):
    ROLE_CHOICES = [
            ('NONE', '\u2014'),
            ('FAC', 'Faculty Member'),
            ('SESS', 'Sessional Instructor'),
            ('COOP', 'Co-op Staff'),
            ('INST', 'Other Instructor'),
            ]

    person = forms.ModelChoiceField(queryset=Person.objects.all(), widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    
InstrRoleFormSet = forms.formsets.formset_factory(InstrRoleForm, extra=0)

class TAForm(forms.Form):
    userid = forms.CharField(required=True, label="Userid", max_length=8, 
        help_text="TA's SFU userid. Must be the ID they use to log in, not an email alias.",
        widget=forms.TextInput(attrs={'size':'9'}))
    fname = forms.CharField(required=False, label="First Name",
        help_text="First name: will eventually be replaced from SIMS database, but need a placeholder for now.",
        widget=forms.TextInput(attrs={'size':'15'}))
    lname = forms.CharField(required=False, label="Last Name",
        help_text="Last name: will eventually be replaced from SIMS database, but need a placeholder for now.",
        widget=forms.TextInput(attrs={'size':'15'}))
    
    def __init__(self, offering, *args, **kwargs):
        super(TAForm, self).__init__(*args, **kwargs)
        self.offering = offering
    
    def clean(self):
        cleaned_data = self.cleaned_data
        if 'userid' not in cleaned_data or len(cleaned_data['userid'])==0:
            # let clean_userid take care of this.
            return cleaned_data

        people = Person.objects.filter(userid=cleaned_data['userid'])
        if len(people)==0 and (not cleaned_data['fname'] or not cleaned_data['lname']):
            raise forms.ValidationError("Userid isn't known to the system: please give more info so this person can be added. Please double-check their userid to make sure it is correct before submitting.")
        return cleaned_data
    
    def clean_userid(self):
        userid = self.cleaned_data['userid']
        if len(userid)<1:
            raise forms.ValidationError("Userid must not be empty.")

        # make sure not already a member somehow.
        ms = Member.objects.filter(person__userid=userid, offering=self.offering)
        for m in ms:
            if m.role == "TA":
                raise forms.ValidationError("That user is already a TA.")
            elif m.role != "DROP":
                raise forms.ValidationError("That user already has role %s in this course." % (m.get_role_display()))

        return userid

class UnitAddressForm(forms.Form):
    informal_name = forms.CharField(required=True, label="Informal Name", max_length=25,
                            help_text='Informal (letterhead) name for the unit (e.g. name without "School of" or "Department").',
                            widget=forms.TextInput(attrs={'size': 20}))
    addr1 = forms.CharField(required=True, label="Address 1", help_text='First address line, e.g. "7654 Academic Quadrangle".',
                            widget=forms.TextInput(attrs={'size': 25}))
    addr2 = forms.CharField(required=True, label="Address 2", initial="8888 University Drive, Burnaby, BC", help_text='Second address line, e.g. "8888 University Drive, Burnaby, BC".',
                            widget=forms.TextInput(attrs={'size': 25}))
    addr3 = forms.CharField(required=False, label="Address 3", initial="Canada V5A 1S6", help_text='Third address line, e.g. "Canada V5A 1S6".',
                            widget=forms.TextInput(attrs={'size': 25}))
    phone = CAPhoneNumberField(required=True, label="Phone Number", initial="778-782-3111", help_text='General phone number for the department',
                            widget=forms.TextInput(attrs={'size': 12}))
    fax = CAPhoneNumberField(required=False, label="Fax Number", help_text='Fax number for the department',
                            widget=forms.TextInput(attrs={'size': 12}))
    web = forms.URLField(required=True, label="Web", help_text="URL of the department's web site")
    email = forms.EmailField(required=False, label="Email", help_text='General contact email for the department')
    deptid = forms.CharField(required=False, label="Dept ID",
                               widget=forms.TextInput(attrs={'size': 5}),
                               help_text='Department ID (cost centre) for financial services. e.g. "12345". Used for TA/RA contracts.')
    card_account = forms.CharField(required=False, label="Card Account", max_length=13,
                               widget=forms.TextInput(attrs={'size': 13}),
                               help_text='Account code for card requisitions (e.g. "12-12345-1234")')
    card_rooms = forms.CharField(required=False, label="Card Access Rooms", help_text='Rooms that all grads have access to, for card access forms. Separate lines with "|" and buildings/rooms with ":", e.g. AQ:1234|AQ:5678.',
                            widget=forms.TextInput(attrs={'size': 40}))

    def __init__(self, unit, *args, **kwargs):
        super(UnitAddressForm, self).__init__(*args, **kwargs)
        self.unit = unit
        if 'address' in unit.config:
            self.initial['addr1'] = unit.config['address'][0]
            if len(unit.config['address']) > 1:
                self.initial['addr2'] = unit.config['address'][1]
            else:
                self.initial['addr2'] = ''
            if len(unit.config['address']) > 2:
                self.initial['addr3'] = unit.config['address'][2]
            else:
                self.initial['addr3'] = ''

        if 'tel' in unit.config:
            self.initial['phone'] = unit.config['tel']
        if 'fax' in unit.config:
            self.initial['fax'] = unit.config['fax']
        if 'web' in unit.config:
            self.initial['web'] = unit.config['web']
        if 'email' in unit.config:
            self.initial['email'] = unit.config['email']
        if 'deptid' in unit.config:
            self.initial['deptid'] = unit.config['deptid']
        if 'card_account' in unit.config:
            self.initial['card_account'] = unit.config['card_account']
        if 'card_rooms' in unit.config:
            self.initial['card_rooms'] = unit.config['card_rooms']
        if 'informal_name' in unit.config:
            self.initial['informal_name'] = unit.config['informal_name']
        else:
            self.initial['informal_name'] = unit.name
    
    def _set_or_delete(self, data, datakey, config, configkey):
        if datakey in data and data[datakey]:
            config[configkey] = data[datakey]
        elif configkey in config:
            del config[configkey]
    
    def copy_to_unit(self):
        data = self.cleaned_data
        addr = []
        if 'addr1' in data and data['addr1']:
            addr.append(data['addr1'])
        if 'addr2' in data and data['addr2']:
            addr.append(data['addr2'])
        if 'addr3' in data and data['addr3']:
            addr.append(data['addr3'])
        self.unit.config['address'] = addr
        
        self._set_or_delete(data, 'phone', self.unit.config, 'tel')
        self._set_or_delete(data, 'fax', self.unit.config, 'fax')
        self._set_or_delete(data, 'web', self.unit.config, 'web')
        self._set_or_delete(data, 'email', self.unit.config, 'email')
        self._set_or_delete(data, 'deptid', self.unit.config, 'deptid')
        self._set_or_delete(data, 'card_account', self.unit.config, 'card_account')
        self._set_or_delete(data, 'card_rooms', self.unit.config, 'card_rooms')
        self._set_or_delete(data, 'phone', self.unit.config, 'tel')
        self._set_or_delete(data, 'informal_name', self.unit.config, 'informal_name')

class SemesterForm(forms.ModelForm):
    def clean_name(self):
        name = self.cleaned_data['name']
        if not name.isdigit():
            raise forms.ValidationError('Must be all digits')
        return name
        
    class Meta:
        model = Semester
        exclude = []
        widgets = {
                'name': forms.TextInput(attrs={'size': 4, 'max_length': 4, 'autofocus': True})
                }


class SemesterWeekForm(forms.ModelForm):
    class Meta:
        model = SemesterWeek
        exclude = ['semester']
    def clean_monday(self):
        date = self.cleaned_data['monday']
        if date.weekday() != 0:
            raise forms.ValidationError('Must be a Monday')
        return date

class BaseSemesterWeekFormset(forms.models.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super(BaseSemesterWeekFormset, self).__init__(*args, **kwargs)
    
    def clean(self):
        if any(self.errors):
            return

        weeks = set()
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if 'week' not in form.cleaned_data or ('DELETE' in form.cleaned_data and form.cleaned_data['DELETE']):
                continue
            week = form.cleaned_data['week']
            if week in weeks:
                raise forms.ValidationError('Weeks must be distinct.')
            weeks.add(week)
        
        if 1 not in weeks:
            raise forms.ValidationError('Must specify Monday of week 1')

SemesterWeekFormset = forms.models.modelformset_factory(SemesterWeek, formset=BaseSemesterWeekFormset, form=SemesterWeekForm,
                                                        max_num=3, extra=2, can_delete=True)

    
class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        exclude = ['semester']

class BaseHolidayFormset(forms.models.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super(BaseHolidayFormset, self).__init__(*args, **kwargs)

HolidayFormset = forms.models.modelformset_factory(Holiday, formset=BaseHolidayFormset, form=HolidayForm,
                                                   max_num=20, extra=5, can_delete=True)



# form for the course browser: never submitted, only rendered and processed with JS
from coredata.models import CAMPUS_CHOICES_SHORT, WQB_FLAGS, CAMPUSES
from itertools import chain
from django.utils.html import conditional_escape
import datetime

class CheckboxSelectTerse(forms.CheckboxSelectMultiple):
    """
    A CheckboxSelectMultiple, but with a more compact rendering
    """
    template_name = 'coredata/_checkbox_select_terse.html'


FLAG_DICT = dict(WQB_FLAGS)
#UNIVERSAL_COLUMNS = ['semester', 'coursecode'] # always display these Just Because.
#COLUMN_CHOICES = [ # columns that can be turned on and off by the user.
#    ('title', 'Course Title'),
#    ('instructors', 'Instructor(s)'),
#    ('enrl_tot', 'Enrolment'),
#    ('campus', 'Campus'),
#    ]
#COLUMN_NAMES = dict(COLUMN_CHOICES)
#COLUMN_NAMES['semester'] = 'Semester'
#COLUMN_NAMES['coursecode'] = 'Course'
#DEFAULT_COLUMNS = ['title', 'enrol', 'instructors', 'campus']
class OfferingFilterForm(forms.Form):
    #columns = forms.MultipleChoiceField(choices=COLUMN_CHOICES, initial=DEFAULT_COLUMNS)
    subject = forms.ChoiceField()
    number = forms.CharField(widget=forms.TextInput(attrs={'size': '3'}), label='Course Number')
    section = forms.CharField(widget=forms.TextInput(attrs={'size': '3'}))
    instructor = forms.CharField(widget=forms.TextInput(attrs={'size': '12'}), label='Instructor Userid')
    campus = forms.ChoiceField(choices=([('', 'all')] + list(CAMPUS_CHOICES_SHORT)))
    semester = forms.ChoiceField()
    crstitle = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), label='Title Contains')
    wqb = forms.MultipleChoiceField(choices=WQB_FLAGS, initial=[], label='WQB',
                                    widget=CheckboxSelectTerse())
    mode = forms.ChoiceField(label='Mode/Time', choices=[('', 'all'), ('dist', 'Distance'), ('on', 'On-Campus'), ('day', 'On-Campus, day'), ('eve', 'On-Campus, evening')])
    space = forms.MultipleChoiceField(label=mark_safe('<span title="Filter either enrollment not at capacity, or no waiting list">Free Space [?]</span>'), choices=[('seats', 'seats'), ('nowait', 'no waitlist')], widget=CheckboxSelectTerse())
    xlist = forms.MultipleChoiceField(label=mark_safe('<span title="Show crosslisted in SIMS">Crosslisted [?]</span>'), choices=[('yes', '')], widget=CheckboxSelectTerse())
    
    @classmethod
    @cached(6*3600)
    def allowed_semesters(self):
        # semester choices: start of good data, to reasonably in the future
        today = datetime.date.today()
        offering_sem = CourseOffering.objects.order_by().values('semester').distinct()
        #timely_sem = Semester.objects.filter(id__in=offering_sem, start__lte=today+datetime.timedelta(days=730), end__gte=today-datetime.timedelta(days=730)).order_by('-name')
        timely_sem = Semester.objects.filter(id__in=offering_sem, name__gte='1101', start__lte=today+datetime.timedelta(days=730)).order_by('-name')
        return timely_sem

    @classmethod
    @cached(6*3600)
    def all_subjects(self, semesters, unit=None):
        subjects = CourseOffering.objects.filter(semester__in=semesters)
        if unit:
            subunits = Unit.sub_unit_ids([unit])
            subjects = subjects.filter(owner__in=subunits)
        return subjects.order_by('subject').values_list('subject', flat=True).distinct()

    def __init__(self, unit, campus, *args, **kwargs):
        super(OfferingFilterForm, self).__init__(*args, **kwargs)
        if campus:
            self.fields['campus'].widget.attrs['disabled'] = 'disabled'
            self.fields['campus'].choices = [('', CAMPUSES[campus]),]

        # semester choices
        semesters = self.allowed_semesters()
        self.fields['semester'].choices = [('', 'all')] + [(s.name, s.label()) for s in semesters]
        # subject choices: all that exist in allowed semesters
        subjects = self.all_subjects(semesters, unit)
        self.fields['subject'].choices = [('', 'all')] + [(s,s) for s in subjects]

class TemporaryPersonForm(forms.Form):
    first_name = forms.CharField(max_length=32, required=True)
    last_name = forms.CharField(max_length=32, required=True)
    email = forms.CharField(max_length=50, required=False,
                    help_text='Person\'s email address')
    sin = forms.CharField(max_length=10, required=False, 
                    help_text='SIN number')

class CourseHomePageForm(forms.Form):
    url = forms.URLField(required=True, label="URL", help_text="URL of the course's main web page")
    maillist = forms.CharField(required=False, label="Mailing List", help_text="The course mailing list. Leave blank for the default. e.g. \"cmpt-100-bby\".")


class AnyPersonForm(forms.ModelForm):

    person = PersonField(required=False)
    #  This is just for admins, so we really shouldn't limit the queryset.  Instead, set the list of AnyPersons to
    #  clearly tell us which FuturePersons were hidden by users so we know it may be safe to delete them if they have
    #  no other foreign key
    #future_person = forms.ModelChoiceField(queryset=FuturePerson.objects.visible(), required=False)
    #role_account = forms.ModelChoiceField(queryset=RoleAccount.objects.all(), required=False)


    class Meta:
        model = AnyPerson
        exclude = []

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(AnyPersonForm, self).is_valid(*args, **kwargs)
    def __init__(self, *args, **kwargs):
        super(AnyPersonForm, self).__init__(*args, **kwargs)
        self.fields['person'].widget.attrs.update({'autofocus': 'autofocus'})

class RoleAccountForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea, required=False)
    class Meta:
        model = RoleAccount
        exclude = ['config']
    def __init__(self, *args, **kwargs):
        super(RoleAccountForm, self).__init__(*args, **kwargs)
        self.fields['userid'].widget.attrs.update({'autofocus': 'autofocus'})
