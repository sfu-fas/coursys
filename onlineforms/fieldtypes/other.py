from django.utils.safestring import mark_safe
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.forms import fields
from onlineforms.fieldtypes.widgets import CustomMultipleInputWidget


class CustomMultipleInputField(fields.MultiValueField):

    def __init__(self, max=5, *args, **kwargs):
        kwargs['widget'] = CustomMultipleInputWidget( max=max)
        field_set = [fields.CharField() for _ in xrange(int(max))]

        super(CustomMultipleInputField, self).__init__(fields=field_set, *args, **kwargs)

    def compress(self, data_list):
        print "COMPRESS"
        print data_list
        if data_list:
            return "|".join(data_list)
        return None


class ListField(FieldBase):
    class ListConfigForm(FieldConfigForm):
        field_length = forms.IntegerField(min_value=1, max_value=500)
        max_responses = forms.IntegerField(min_value=1, max_value=20)

    def make_config_form(self):
        return self.ListConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):

        return CustomMultipleInputField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            max=self.config['max_responses'])

    def serialize_field(self, cleaned_data):
        return{'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError


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
