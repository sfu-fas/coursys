from django.utils.safestring import mark_safe
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from onlineforms.fieldtypes.widgets import CustomMultipleInputWidget

class ListField(FieldBase, forms.MultiValueField):
    class ListConfigForm(FieldConfigForm):
        field_length = forms.IntegerField(min_value=1, max_value=500)
        max_responses = forms.IntegerField(min_value=1, max_value=20)

    def make_config_form(self):
        return self.ListConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):

        return forms.MultiValueField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            widget=CustomMultipleInputWidget(attrs=self.config))

    def serialize_field(self, cleaned_data):
        return{'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError

    def compress(self, value):
        "Compress each field into a single string"
        if value:
            return "|".join(value)
        return None


class FileCustomField(FieldBase):
    class FileConfigForm(FieldConfigForm):
        max_length = forms.IntegerField(min_value=1, max_value=500)

    def make_config_form(self):
        return self.FileConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        return forms.FileField(required=self.config['required'],
                label=self.config['label'],
                help_text=self.config['help_text'],
                max_length=int(self.config['max_length']))

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + "File title?" + '</p>')


class URLCustomField(FieldBase):
    #Can use URLField
    class URLConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
      return self.URLConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.URLField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

        return c

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError


class DividerField(FieldBase):
    configurable = False

    def make_config_form(self):
        return self.configurable

    def make_entry_field(self, fieldsubmission=None):
        from onlineforms.forms import DividerFieldWidget
        return forms.CharField(required=False,
            widget=DividerFieldWidget(),
            label='',
            help_text='')

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<hr />')
