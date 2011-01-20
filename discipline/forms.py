from django import forms
from discipline.models import DisciplineGroup

class DisciplineGroupForm(forms.ModelForm):
    students = forms.MultipleChoiceField(choices=[])

    class Meta:
        model = DisciplineGroup
        exclude = ('offering',)


