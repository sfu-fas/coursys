from django import forms
from dashboard.models import NewsItem

class FeedSetupForm(forms.Form):
    agree = forms.BooleanField(required=False)
    
    def clean_agree(self):
        data = self.cleaned_data['agree']
        if not data:
            raise forms.ValidationError("You must agree to continue")
        return data

class NewsConfigForm(forms.Form):
    want_email = forms.BooleanField(required=False, label="Send Email", help_text="Send emails of new notifications to your email?")
    
class SignatureForm(forms.Form):
    person = forms.ChoiceField(choices=[])
    signature = forms.ImageField(required=True, help_text="Must be a PNG image, scanned at 200dpi: around 100 pixels high and 600 pixels wide.")
    
    def clean_signature(self):
        sig = self.cleaned_data['signature']
        # TODO: check image type/size/colours
        return sig
    
class PhotoAgreementForm(forms.Form):
    agree = forms.BooleanField(required=False, label="Do you agree?", help_text="I acknowledge that I have read and will abide by this agreement.")

