from django import forms
from django.forms.models import ModelForm
from models import Alert, AlertType, AlertUpdate, AlertEmailTemplate
from django.template import Template, TemplateSyntaxError

class EmailForm(ModelForm):
    class Meta:
        model = AlertEmailTemplate
        exclude = ('alerttype', 'created_at', 'created_by', 'hidden')

    def clean_content(self):
        content = self.cleaned_data['content']
        try:
            Template(content)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
        return content
