from django import forms
from submission.models import STATUS_CHOICES, TYPE_CHOICES
from django.forms.widgets import RadioSelect

class AddComponentForm(forms.Form):
    type = forms.ChoiceField(widget=RadioSelect(),choices=TYPE_CHOICES,required=True)
    title = forms.CharField(max_length=30, label='Title', help_text = 'Name for this component (e.g. "Part 1" or "Programming Section")')
    position = forms.IntegerField(min_value=0)

class AddSummissionForm(forms.Form):
    pass
    