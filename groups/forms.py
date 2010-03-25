from django.forms import ModelForm
from django import forms
from grades.models import Activity
from coredata.models import Person
from django.forms.util import flatatt
from groups.models import Group

class GroupForm(ModelForm):
    class Meta:
        model = Group
        fields = ['name']


class ActivityForm(forms.Form):
    selected = forms.BooleanField(label = 'Selected Activity:', required = False)
    
    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields.widget.attrs['readonly'] = True

        
class StudentForm(forms.Form):
    selected = forms.BooleanField(label = 'Selected Student:', required = False)


    

    
