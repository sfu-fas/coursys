from django import forms
from ta.models import TUG

class TUGForm(forms.ModelForm):
    class Meta:
        model = TUG
