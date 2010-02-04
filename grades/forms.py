from django import forms
from grades.models import ACTIVITY_STATUS_CHOICES, NumericActivity

class NumericActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label='Name:')
    short_name = forms.CharField(max_length=15, label='Short name:')
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label='Status:')
    due_date = forms.DateTimeField(required=False, label='Due date:')
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage:')
    max_grade = forms.DecimalField(max_digits=5, decimal_places=2, label='Maximum grade:')
    specify_numeric_formula = forms.BooleanField(label='Specify formula:', required=False)
    
class LetterActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label='Name:')
    short_name = forms.CharField(max_length=15, label='Short name:')
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label='Status:')
    due_date = forms.DateTimeField(required=False, label='Due date:')
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage:')
    specify_letter_formula = forms.BooleanField(label='Specify formula:', required=False)


class _MyModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name
    
#Todo: Not yet complete, to be combined with LetterActivityForm
class CalLetterActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label='Name:')
    short_name = forms.CharField(max_length=15, label='Short name:')
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label='Status:')
    due_date = forms.DateTimeField(required=False, label='Due date:')
    numeric_activity = _MyModelChoiceField(queryset=NumericActivity.objects.none(), empty_label=None)
    
    def __init__(self, course_slug, *args, **kwargs):
        super(CalLetterActivityForm, self).__init__(*args, **kwargs)
        self.fields['numeric_activity'].queryset = NumericActivity.objects.filter(offering__slug=course_slug)
    

