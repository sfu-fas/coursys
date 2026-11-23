from django import forms

from system.models import SystemVariable


class SystemVariableForm(forms.ModelForm):
    class Meta:
        model = SystemVariable
        fields = ['key', 'label', 'value_type', 'value', 'unit', 'notes']

    def __init__(self, *args, **kwargs):
        super(SystemVariableForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['key'].disabled = True
