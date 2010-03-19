from django.forms import ModelForm
from django import forms
from grades.models import Activity

class GroupForm(forms.Form):
    name=forms.CharField(max_length=30, label='Name:')
    manager=forms.CharField(max_length=20, label='Group Manager:')


    
    #TODO Invite students to the group

class ActivityForm(ModelForm):
    selected = forms.BooleanField(label = 'Selected Activity:', required = False)
    
    class Meta:
        model = Activity
        fields = ["selected","name","percent","due_date"]
    
