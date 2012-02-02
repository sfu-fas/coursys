from django import forms
from ra.models import RAAppointment, Account, Project
from coredata.models import Person, Role

HIRING_FACULTY_CHOICES = [(p.userid, (p.last_name + ", " + p.first_name)) \
    for p in Person.objects.all() \
    if Role.objects.filter(person__userid=p.userid, role="FUND").count() > 0]

class RAAppointmentForm(forms.Form):
    hiring_faculty = forms.ChoiceField(choices = HIRING_FACULTY_CHOICES)
