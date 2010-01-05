from django import forms

class ImportForm(forms.Form):
    passwd = forms.CharField(widget=forms.PasswordInput(render_value=False),
            label='Database password', max_length=20)
