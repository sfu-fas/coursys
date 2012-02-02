from django import forms
from ra.models import RAAppointment, Account, Project
from coredata.models import Person

HIRING_FACULTY_CHOICES = [(p.emplid, (p.last_name + ", " + p.first_name)) for p in Person.objects.all()]

class RAAppointmentForm(forms.Form):
    hiring_faculty = forms.ChoiceField(choices = HIRING_FACULTY_CHOICES)
