from django import forms
from coredata.models import Role, Person

#class ImportForm(forms.Form):
#    passwd = forms.CharField(widget=forms.PasswordInput(render_value=False),
#            label='Database password', max_length=20)

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
