from django import forms
from models import TeachingEquivalent
from django.forms.widgets import TextInput, Textarea

class TeachingEquivFormInstructor(forms.ModelForm):
    class Meta:
        model = TeachingEquivalent
        exclude = ('status', 'instructor')
        widgets = {
                   'credits_numerator': TextInput(attrs={'size': 5}),
                   'credits_denominator': TextInput(attrs={'size': 5}),
                   'summary': TextInput(attrs={'size': 60}),
                   'comment': Textarea(attrs={'cols': 60, 'rows': 15}),
                   }