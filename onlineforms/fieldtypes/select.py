from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms

class RadioSelectField(FieldBase):
    class RadioSelectConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError


class DropdownSelectField(FieldBase):

    choices = True

    class DropdownSelectConfigForm(FieldConfigForm):

        def __init__(self, config=None):
            super(self.__class__, self).__init__(config)

            self.config = config

            keys = self.find_keys("choice_")

            for k in keys:
                self.fields[k] = forms.CharField(required=False, label="Choice")

        def find_keys(self, start):
            return [c for c in self.config if c.startswith(start) and self.config[c]]


    def make_config_form(self):
        config = self.DropdownSelectConfigForm(self.config)
        return config

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError



class MultipleSelectField(FieldBase):
    class MultipleSelectConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        raise NotImplementedError

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError