from django import forms
from coredata.models import Role, Person, Member

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
    class Meta:
        model = Person

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
    
    def __init__(self, offering, *args, **kwargs):
        super(TAForm, self).__init__(*args, **kwargs)
        self.offering = offering
        
    def clean_userid(self):
        userid = self.cleaned_data['userid']
        if len(userid)<1:
            raise forms.ValidationError, "Userid must not be empty."

        # make sure not already a member somehow.
        ms = Member.objects.filter(person__userid=userid, offering=self.offering)
        if ms:
            m = ms[0]
            if m.role == "TA":
                raise forms.ValidationError, "That user is already a TA."
            elif m.role != "DROP":
                raise forms.ValidationError, "That user already has role %s in this course." % (m.get_role_display())

        return userid
    
class TALongForm(TAForm):
    pass
