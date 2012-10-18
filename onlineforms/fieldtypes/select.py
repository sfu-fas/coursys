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
    class DropdownSelectConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.DropdownSelectConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        raise NotImplementedError

    def serialize_field(self, field):
        raise NotImplementedError

    def to_html(self, fieldsubmission=None):
        raise NotImplementedError

    def require_choices(self):
        return True


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