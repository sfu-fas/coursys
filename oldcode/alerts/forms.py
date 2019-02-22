from django import forms
from django.forms.models import ModelForm
from .models import Alert, AlertType, AlertUpdate, AlertEmailTemplate
from django.template import Template, TemplateSyntaxError

class AlertTypeForm(ModelForm):
    class Meta:
        model = AlertType
        exclude = ('hidden', 'config') 

class EmailForm(ModelForm):
    class Meta:
        model = AlertEmailTemplate
        exclude = ('alerttype', 'created_at', 'created_by', 'hidden', 'config')

    def clean_content(self):
        content = self.cleaned_data['content']
        try:
            Template(content)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + str(e))
        return content

class ResolutionForm(ModelForm):
    class Meta:
        model = AlertUpdate 
        exclude = ('alert', 'update_type', 'created_at', 'hidden')

class EmailResolutionForm(ModelForm):
    from_email = forms.CharField( label="From", required=True )
    to_email = forms.CharField( label="To", required=True )
    subject = forms.CharField( label="Subject", required=True )
    class Meta:
        model = AlertUpdate
        fields = ('to_email', 'from_email', 'subject', 'comments', 'resolved_until')

class AlertUpdateForm(ModelForm):
    class Meta:
        model = AlertUpdate
        exclude = ('alert', 'update_type', 'created_at', 'hidden', 'resolved_until' )

