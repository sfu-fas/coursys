from django import forms
from django.forms.models import ModelForm
from onlineforms.models import Field, FIELD_TYPE_CHOICES

            
"""class DividerField(forms.CharField):
    def __init__(self, label='', *args, **kwargs):
        super(DividerField, self).__init__(label, *args, **kwargs)
        
    def render(self):
        return mark_safe('<hr />')
        
    def clean(self, value):
        return value"""

        
class FieldForm(forms.Form):
    type = forms.ChoiceField(required=True, choices=FIELD_TYPE_CHOICES, label='Type')


class DynamicForm(forms.Form):
    def __init__(self, title, *args, **kwargs):
        self.title = title
        super(DynamicForm, self).__init__(*args, **kwargs)

    def setFields(self, kwargs):
        """
        Sets the fields in a form
        """
        keys = kwargs.keys()

        # Determine order right here
        keys.sort()

        for k in keys:
            self.fields[k] = kwargs[k]

    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name, field in self.fields.items():
            try:
                field.clean(post[name])
            except ValidationError, e:
                elf.errors[name] = e.messages
