from django import forms
from dashboard.models import *

class MessageForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        # these fields are decided from the request at the time the form is submitted
        exclude = ['user', 'author', 'published','updated','source_app','course', 'read']

class FeedSetupForm(forms.Form):
    agree = forms.BooleanField(required=False)
    
    def clean_agree(self):
        data = self.cleaned_data['agree']
        if not data:
            raise forms.ValidationError("You must agree to continue")
        return data

class NewsConfigForm(forms.Form):
    want_email = forms.BooleanField(required=False, label="Send Email", help_text="Send emails of new notifications to your email?")
    

