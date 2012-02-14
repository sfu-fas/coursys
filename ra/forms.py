from django import forms
from ra.models import RAAppointment, Account, Project, \
                      HIRING_CATEGORY_CHOICES, PAY_TYPE_CHOICES
from coredata.models import Person, Role
#from django.core.exceptions import ObjectDoesNotExist

class RAForm(forms.ModelForm):
    person = forms.CharField(label='Hire')

    def clean_person(self):
        return Person.objects.get(emplid=self.cleaned_data['person'])

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data 
        

    class Meta:
        model = RAAppointment
        exclude = ('config',)
