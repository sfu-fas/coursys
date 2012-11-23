from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.forms import fields
from onlineforms.fieldtypes.widgets import CustomMultipleInputWidget


class CustomMultipleInputField(fields.MultiValueField):
    def __init__(self, name="", max=20, min=2, other_required=False, *args, **kwargs):
        self.min = min
        self.max = max
        self.required = other_required
        kwargs['widget'] = CustomMultipleInputWidget(name=name, max=max, min=min)
        self.field_set = [fields.CharField() for _ in xrange(int(max))]

        super(CustomMultipleInputField, self).__init__(fields=self.field_set, *args, **kwargs)


    def compress(self, data_list):
        if data_list:
            name = data_list.items()[1][0][0]
            count = 0
            data = []

            for k, v in sorted(data_list.iteritems(), key=lambda (k,v): (k,v)):
                if str(k).startswith(str(name) + '_'):
                    if len(str(v)) > 0:
                        data.append(v)
                        count += 1

            if self.required and count < int(self.min):
                raise ValidationError, 'Enter at least '+self.min+' responses'

            return data
        return None


class ListField(FieldBase):
    class ListConfigForm(FieldConfigForm):
        max_responses = forms.IntegerField(min_value=1, max_value=20, initial=5)
        min_responses = forms.IntegerField(min_value=1, max_value=10, initial=2)

    def make_config_form(self):
        return self.ListConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        return CustomMultipleInputField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            min=self.config['min_responses'],
            max=self.config['max_responses'],
            name=self.config['label'],
            other_required=self.config['required'])


    def serialize_field(self, cleaned_data):
        return{'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        infos = fieldsubmission.data['info']
        html = '<ul>'
        for info in infos:
            html += '<li>' + info + '</li>'
        html += '</ul>'

        return mark_safe(html)


class FileCustomField(FieldBase):
    class FileConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.FileConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        return forms.FileField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

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
