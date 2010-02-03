from django import forms
from coredata.models import Role

class ImportForm(forms.Form):
    passwd = forms.CharField(widget=forms.PasswordInput(render_value=False),
            label='Database password', max_length=20)

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
