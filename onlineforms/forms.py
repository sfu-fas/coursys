from django.forms.models import ModelForm
from django import forms
from onlineforms.models import Field, FIELD_TYPE_CHOICES


class ConfigFieldForm(forms.Form):
    RADIO_CHOICES=(
        ('yes', 'Required'),
        ('no', 'Not required'),
    )

    name = forms.CharField(required=True, label='name', help_text='test')
    type = forms.ChoiceField(required=True, choices=FIELD_TYPE_CHOICES, label='Type')
    size = forms.IntegerField(required=True, label='length', help_text='length')
    required = forms.ChoiceField(required=True,
        label='required',
        choices=RADIO_CHOICES,
        widget=forms.RadioSelect())
    class Meta:
        model = Field


class DynamicForm(forms.Form):    
    def setFields(self, kwargs):
        """
        Sets the fields in a form
        """
        keys = kwargs.keys()
        
        # Determine order right here
        keys.sort()
        
        for k in keys:
            self.fields[k] = kwargs[k]
            
    def setData(self, kwargs):
        """
        Sets given data in the form
        """
        keys = kwargs.keys()
        
        # Determine order right here
        keys.sort()
        
        for k in keys:
            self.data[k] = kwargs[k]
            
    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name, field in self.fields.items():
            try:
                field.clean(post[name])
            except ValidationError, e:
                elf.errors[name] = e.messages