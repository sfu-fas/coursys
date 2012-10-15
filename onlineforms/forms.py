from django import forms
from django.forms.models import ModelForm
from onlineforms.models import Field, FIELD_TYPE_CHOICES, FIELD_TYPE_MODELS


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

    def fromFields(self, fields):
        """
        Sets the fields from a list of field model objects
        preserving the order they are given in
        """
        fieldargs = {}
        for (counter, field) in enumerate(fields):
            display_field = FIELD_TYPE_MODELS[field.fieldtype](field.config)
            fieldargs[counter] = display_field.make_entry_field()
        self.setFields(fieldargs)


    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name, field in self.fields.items():
            try:
                field.clean(post[name])
            except ValidationError, e:
                elf.errors[name] = e.messages
