from django import forms
from advisornotes.models import AdvisorNote

class AdvisorNoteForm(forms.ModelForm):
    class Meta:
        model = AdvisorNote