from django import forms

class PrivacyForm(forms.Form):
    agree = forms.BooleanField(required=True, label="I agree")
