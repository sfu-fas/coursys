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

            keys = [c for c in self.config if c.startswith("choice_") and self.config[c]]

            for k in keys:
                self.fields[k] = forms.CharField(required=False, label="Choice")


    def make_config_form(self):
        config = self.DropdownSelectConfigForm(self.config)
        return config

    def make_entry_field(self, fieldsubmission=None):

        the_choices = [(k,v) for k,v in self.config.iteritems() if k.startswith("choice_") and self.config[k]]

        c = forms.ChoiceField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            choices = the_choices)

        return c

    def serialize_field(self, field):
        return {'choice': unicode(field.clean())}

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