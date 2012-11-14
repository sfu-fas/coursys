from django import forms
from coredata.models import Role, Person, Member, Course, CourseOffering, Unit, Semester, SemesterWeek, Holiday, ComputingAccount
from coredata.queries import find_person, add_person, SIMSProblem
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.contrib.localflavor.ca.forms import CAPhoneNumberField

class OfferingSelect(forms.Select):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        """
        Render for jQueryUI autocomplete widget
        """
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(value)
        return mark_safe(u'<input%s />' % forms.widgets.flatatt(final_attrs))

class OfferingField(forms.ModelChoiceField):
    """
    Override ModelChoiceField so we don't have to build CourseOffering.objects.all()
    unnecessarily, and can set other parameters appropriately.
    """
    def __init__(self, *args, **kwargs):
        super(OfferingField, self).__init__(*args, queryset=CourseOffering.objects.none(), widget=OfferingSelect(attrs={'size': 30}), help_text="Type to search for course offerings.", **kwargs)
        
    def to_python(self, value):
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
                   'label': forms.TextInput(attrs={'size': 5}),
                   'name': forms.TextInput(attrs={'size': 40}),
                   'acad_org': forms.TextInput(attrs={'size': 10}),
                   }

    # from http://stackoverflow.com/a/1400046/1236542
    def clean_acad_org(self):
        acad_org = self.cleaned_data['acad_org']
        if acad_org == '':
            acad_org = None
        return acad_org

class MemberForm(forms.ModelForm):
    person = forms.CharField(min_length=1, max_length=8, label='SFU Userid')
    offering = OfferingField()
    
    def clean_person(self):
        userid = self.cleaned_data['person']
        person = Person.objects.filter(userid=userid)
        if person:
            return person[0]
        else:
            raise forms.ValidationError, "Userid '%s' is unknown."%(userid)
    
    class Meta:
        model = Member
        exclude = ('config', 'official_grade')

class PersonForm(forms.ModelForm):
    emplid = forms.CharField(max_length=9,
                    help_text='Employee ID (i.e. student number).  Enter a number starting with "0000" if unknown: will be filled in based on userid at next import',
                    widget=forms.TextInput(attrs={'size':'9'}))
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

class PersonWidget(forms.TextInput):
    """
    A widget to allow selecting a person by emplid, where they might not be in the coredata.Person table yet
    """
    def __init__(self, *args, **kwargs):
        self.found_sims = False
        return super(PersonWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if self.found_sims:
            textwidget = super(PersonWidget, self).render(name, value, attrs)
            confirmwidget = ' Import %s %s (%s) from SIMS: ' % (self.sims_data['first_name'], self.sims_data['last_name'], self.sims_data['emplid'])
            confirmwidget += '<input type="checkbox" name="%s_confirm" />' % (name)
            confirmwidget += '<input type="hidden" name="%s_emplid" value="%s" />' % (name, self.sims_data['emplid'])
            return textwidget + confirmwidget
        else:
            return super(PersonWidget, self).render(name, value, attrs)


class PersonField(forms.CharField):
    """
    A field to allow emplid entry of a Person, but will find new people from SIMS if they aren't
    already a coredata.Person.

    If using, must override is_valid in your form as:
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(MyFormClass, self).is_valid(*args, **kwargs)
    
    You might also want to autocomplete for people in the system: 
    $('#id_person').each(function() {
      $(this).autocomplete({
        source: '/data/students',
        minLength: 2,
        select: function(event, ui){
          $(this).data("val", ui.item.value);
        }
      });
    });  
    """
    def __init__(self, *args, **kwargs):
        widget = PersonWidget()
        kwargs['widget'] = widget
        return super(PersonField, self).__init__(*args, **kwargs)
    
    #def to_python(self, value):
    def clean(self, value):
        if isinstance(value, Person):
            return value
        else:
            try:
                return Person.objects.get(emplid=value)
            except (ValueError, Person.DoesNotExist):
                # try to find the emplid in SIMS if they are missing from our DB
                if not value or not value.isdigit():
                    cas = ComputingAccount.objects.filter(userid=value)
                    if cas:
                        value = cas[0].emplid
                    else:
                        raise forms.ValidationError, "Could not find this emplid."
                try:
                    persondata = find_person(value)
                except SIMSProblem, e:
                    raise forms.ValidationError, "Problem locating person in SIMS: " + e.message
                if not persondata:
                    raise forms.ValidationError, "Could not find this emplid."
                
                # we found this emplid in SIMS: raise validation error, but offer to add next time.
                confirm = self.fieldname+'_confirm'
                checkemplid = self.fieldname+'_emplid'
                if confirm in self.formdata and checkemplid in self.formdata and self.formdata[checkemplid] == value:
                    # new person was presented in the form last time, and they confirmed import
                    p = add_person(value)
                    return p
                else:
                    self.widget.found_sims = True
                    self.widget.sims_data = persondata
                    raise forms.ValidationError, "Person is new to this system: please confirm their import."
    
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


class RoleForm(forms.ModelForm):
    person = PersonField(label="Emplid", help_text="or type to search")
    class Meta:
        model = Role
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(RoleForm, self).is_valid(*args, **kwargs)

class UnitRoleForm(RoleForm):
    role = forms.ChoiceField(widget=forms.RadioSelect())


class InstrRoleForm(forms.Form):
    ROLE_CHOICES = [
            ('NONE', u'\u2014'),
            ('FAC', 'Faculty Member'),
            ('SESS', 'Sessional Instructor'),
            ('COOP', 'Co-op Staff'),
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
            raise forms.ValidationError, "Userid isn't known to the system: please give more info so this person can be added. Please double-check their userid to make sure it is correct before submitting."
        return cleaned_data
    
    def clean_userid(self):
        userid = self.cleaned_data['userid']
        if len(userid)<1:
            raise forms.ValidationError, "Userid must not be empty."

        # make sure not already a member somehow.
        ms = Member.objects.filter(person__userid=userid, offering=self.offering)
        for m in ms:
            if m.role == "TA":
                raise forms.ValidationError, "That user is already a TA."
            elif m.role != "DROP":
                raise forms.ValidationError, "That user already has role %s in this course." % (m.get_role_display())

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
    web = forms.URLField(required=True, label="Web", help_text="URL of the department's web site", verify_exists=True)
    email = forms.EmailField(required=False, label="Email", help_text='General contact email for the department')
    deptid = forms.CharField(required=False, label="Dept ID",
                               widget=forms.TextInput(attrs={'size': 5}),
                               help_text='Department ID (cost centre) for financial services. e.g. "12345". Used for TA/RA contracts.')

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
                'name': forms.TextInput(attrs={'size': 4, 'max_length': 4})
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



