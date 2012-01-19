from django import forms
from advisornotes.models import AdvisorNote

class AdvisorNoteForm(forms.ModelForm):
    class Meta:
        model = AdvisorNote
        
class StudentSearchForm(forms.Form):
        search = forms.CharField(label="Userid or student number",
             widget=forms.TextInput(attrs={'size':'15'}))