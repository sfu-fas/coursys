from models import Contact
from django import forms


class ContactForm(forms.modelForm):
    class Meta:
        model = Contact
        exclude = ['config', 'deleted']
