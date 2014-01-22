from django import forms
#from django.forms.models import imlineformset_factory


from models import DocumentAttachment


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment 
