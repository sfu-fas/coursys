from django import forms
from coredata.models import Role, Person, Member, CourseOffering
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

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


class RoleForm(forms.ModelForm):
    person = forms.CharField(min_length=1, max_length=8, label='SFU Userid')
    
    def clean_person(self):
        userid = self.cleaned_data['person']
        person = Person.objects.filter(userid=userid)
        if person:
            return person[0]
        else:
            raise forms.ValidationError, "Userid '%s' is unknown."%(userid)
    
    class Meta:
        model = Role


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
        exclude = ('config',)

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
    

class InstrRoleForm(forms.Form):
    ROLE_CHOICES = [
            ('NONE', u'\u2014'),
            ('FAC', 'Faculty Member'),
            ('SESS', 'Sessional Instructor'),
            ('COOP', 'Co-op Staff'),
            ]
    def clean_department(self):
        data = self.cleaned_data
        if data['role']!='NONE' and data['department']=='':
            raise forms.ValidationError, "Required to set role."
        return data['department']
    person = forms.ModelChoiceField(queryset=Person.objects.all(), widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    department = forms.CharField(max_length=4, required=False)
    
InstrRoleFormSet = forms.formsets.formset_factory(InstrRoleForm, extra=0)

class TAForm(forms.Form):
    userid = forms.CharField(required=True, label="Userid",
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
