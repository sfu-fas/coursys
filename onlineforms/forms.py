from django.forms.models import ModelForm
from django import forms
from onlineforms.models import Field, FIELD_TYPE_CHOICES

class FieldForm(forms.Form):
    RADIO_CHOICES = (
        ('yes', 'Required'),
        ('no', 'Not required'),
        )

    name = forms.CharField(required=True, label='name', help_text='test')
    type = forms.ChoiceField(required=True, choices=FIELD_TYPE_CHOICES, label='Type')
    required = forms.ChoiceField(required=True,
        label='required',
        choices=RADIO_CHOICES,
        widget=forms.RadioSelect())

    class Meta:
        model = Field

