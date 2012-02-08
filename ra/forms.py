from django import forms
from ra.models import RAAppointment, Account, Project, \
                      HIRING_CATEGORY_CHOICES, PAY_TYPE_CHOICES
from coredata.models import Person, Role
#from django.core.exceptions import ObjectDoesNotExist

HIRING_FACULTY_CHOICES = [(p.userid, (p.last_name + ", " + p.first_name)) \
    for p in Person.objects.all() \
    if Role.objects.filter(person__userid=p.userid, role="FUND").count() > 0]

class RAForm(forms.ModelForm):
    person = forms.CharField(label='Hire')
    hiring_faculty = forms.ChoiceField(choices=HIRING_FACULTY_CHOICES)
    hiring_category = forms.ChoiceField(choices=HIRING_CATEGORY_CHOICES,
                                        required=False)
    project = forms.IntegerField()
    fund = forms.IntegerField()
    account = forms.IntegerField()
    position = forms.IntegerField(required=False)
    reappointment = forms.BooleanField(required=False)
    pay_type = forms.ChoiceField(choices=PAY_TYPE_CHOICES, required=False)
    pay_amount = forms.DecimalField(required=False)
    employment_hours = forms.IntegerField(required=False)
    employment_minutes = forms.IntegerField(required=False)
    units = forms.DecimalField(required=False)
    medical_benefits = forms.BooleanField(required=False)
    dental_benefits = forms.BooleanField(required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea)
    comments = forms.CharField(required=False, widget=forms.Textarea)

    def clean_person(self):
        return Person.objects.get(emplid=self.cleaned_data['person'])

    def clean_hiring_faculty(self):
        return Person.objects.get(userid=self.cleaned_data['hiring_faculty'])

    def clean(self):
        cleaned_data = super(RAForm, self).clean()
        account = cleaned_data.get('account')
        try:
            account_object = Account.objects.get(account_number=account)
            cleaned_data['account'] = account_object
        except Account.DoesNotExist:
            position = cleaned_data.get('position')
            new_account = Account(account_number=account,
                                  position_number=position)
            new_account.save()
            cleaned_data['account'] = new_account
        project = cleaned_data.get('project')
        try:
            project_object = Project.objects.get(project_number=project)
            cleaned_data['project'] = project_object
        except Project.DoesNotExist:
            fund = cleaned_data.get('fund')
            new_project = Project(project_number=project,
                                  fund_number=fund)
            new_project.save()
            cleaned_data['project'] = new_project
        return cleaned_data 
        

    class Meta:
        model = RAAppointment
        fields = ('person',
                  'hiring_faculty',
                  'hiring_category',
                  'project',
                  'fund',
                  'account',
                  'position',
                  'start_date',
                  'end_date',
                  'reappointment',
                  'pay_type',
                  'pay_amount',
                  'employment_hours',
                  'employment_minutes',
                  'units',
                  'medical_benefits',
                  'dental_benefits',
                  'notes',
                  'comments',
                  )