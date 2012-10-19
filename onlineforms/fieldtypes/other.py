from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms

class ListField(FieldBase):
    class ListConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError


class FileCustomField(FieldBase):
    #Can use FileField
    class FileConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError


class URLCustomField(FieldBase):
    #Can use URLField
    class URLConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError

  
class DividerField(FieldBase):
    configurable = False
            
    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        from onlineforms.forms import DividerFieldWidget
        return forms.CharField(required=False,
            widget=DividerFieldWidget(),
            label='',
            help_text='')

    def serialize_field(self, field):
        return {'info': unicode(field.clean())}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<hr />')
