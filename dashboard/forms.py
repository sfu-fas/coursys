from django import forms
from dashboard.models import *

class MessageForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        # these 3 fields are decided from the request ant the time the form is submitted
        exclude = ['user', 'author', 'published','updated','source_app','course']

class FeedSetupForm(forms.Form):
    agree = forms.BooleanField(required=False)
    
    def clean_agree(self):
        data = self.cleaned_data['agree']
        if not data:
            raise forms.ValidationError("You must agree to continue")
        return data

