# Django
from django import forms
# App
from .models import TACategory, TAContract, TACourse

class TACategoryForm(forms.ModelForm):
    class Meta:
        model = TACategory 

class TAContractForm(forms.ModelForm):
    class Meta:
        model = TAContract

class TACourseForm(forms.ModelForm):
    class Meta:
        model = TACourse
