from django import forms
from ra.models import RAAppointment, Account, Project, HIRING_CATEGORY_CHOICES
from coredata.models import Person, Role

HIRING_FACULTY_CHOICES = [(p.userid, (p.last_name + ", " + p.first_name)) \
    for p in Person.objects.all() \
    if Role.objects.filter(person__userid=p.userid, role="FUND").count() > 0]

class RAAppointmentForm(forms.ModelForm):
    person = forms.CharField(label='Hire')
    hiring_faculty = forms.ChoiceField(choices = HIRING_FACULTY_CHOICES)
    hiring_category = forms.ChoiceField(choices = HIRING_CATEGORY_CHOICES,
                                        required = False)
    project = forms.CharField()
    fund_number = forms.CharField()
    account = forms.CharField()
    position_number = forms.CharField()

    class Meta:
        model = RAAppointment
        fields = ('person',
                  'hiring_faculty',
                  'hiring_category',
                  'project',
                  'fund_number',
                  'account',
                  'position_number',
                  'start_date',
                  'end_date',
                  'pay_type',
                  'pay_amount',
                  'employment_hours',
                  'employment_minutes',
                  'units',
                  'reappointment',
                  'medical_benefits',
                  'dental_benefits',
                  'notes',
                  'comments',
                  )
