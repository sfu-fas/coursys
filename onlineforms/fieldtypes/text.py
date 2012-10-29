from django.db.models.fields import TextField
from django.forms.fields import EmailField, CharField
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape

class SmallTextField(FieldBase):
    class SmallTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=300)
        max_length = forms.IntegerField(min_value=1, max_value=300)

    def make_config_form(self):
        return self.SmallTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.CharField(required=self.config['required'],
            widget=forms.TextInput(attrs=
                {'size': min(60, int(self.config['max_length'])),
                 'maxlength': int(self.config['max_length'])}),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class MediumTextField(FieldBase):
    class MediumTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=400)
        max_length = forms.IntegerField(min_value=1, max_value=400)

    def make_config_form(self):
        return self.MediumTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '3'}),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class LargeTextField(FieldBase):
    class LargeTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=500)
        max_length = forms.IntegerField(min_value=1, max_value=500)

    def make_config_form(self):
        return self.LargeTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '15'}),
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']
        if self.config['min_length'] and int(self.config['min_length']) > 0:
            c.min_length = self.config['min_length']
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            c.max_length = self.config['max_length']
        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['info']) + '</p>')


class EmailTextField(FieldBase):
    class EmailTextConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.EmailTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.EmailField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['email']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(fieldsubmission.data['email']) + '</p>')


class ExplanationTextField(FieldBase):
    class ExplanationTextConfigForm(FieldConfigForm):
        max_length = forms.IntegerField(min_value=1, max_value=300)
        text_explanation = forms.CharField(required=True, max_length=500, 
            widget=forms.Textarea(attrs={'cols': '60', 'rows': '15'}))

    def make_config_form(self):
        return self.ExplanationTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        from onlineforms.forms import ExplanationFieldWidget
        c = forms.CharField(required=False,
            label=self.config['label'],
            help_text=self.config['help_text'],
            widget=ExplanationFieldWidget(attrs={'class': 'disabled', 'readonly': 'readonly'}))

        if 'text_explanation' in self.config:
            c.initial = self.config['text_explanation']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(self.config['text_explanation']) + '</p>')

