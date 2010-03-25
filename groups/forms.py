from django.forms import ModelForm
from django import forms
from grades.models import Activity
from coredata.models import Person
from django.forms.util import flatatt

class GroupForm(forms.Form):
    name=forms.CharField(max_length=30, label='Name:')
    manager=forms.CharField(max_length=20, label='Group Manager:')


class ActivityForm(forms.Form):
    selected = forms.BooleanField(label = 'Selected Activity:', required = False)
    
    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields.widget.attrs['readonly'] = True

        
class StudentForm(forms.Form):
    selected = forms.BooleanField(label = 'Selected Student:', required = False)


    

    
