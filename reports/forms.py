from django import forms
from django.forms.models import ModelForm
from .models import Report, HardcodedReport, Query, AccessRule, ScheduleRule
from coredata.forms import PersonField

class ReportForm(ModelForm):
    class Meta:
        model = Report
        exclude = ('config', 'created_at', 'hidden')

class HardcodedReportForm(ModelForm):
    class Meta:
        model = HardcodedReport
        exclude = ('report', 'hidden', 'config', 'created_at') 

class QueryForm(ModelForm):
    class Meta:
        model = Query
        exclude = ('report', 'hidden', 'config', 'created_at') 

class AccessRuleForm(ModelForm):
    person = PersonField(label="Emplid", help_text="or type to search")
    class Meta:
        model = AccessRule
        exclude = ('report', 'hidden', 'config', 'created_at')
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(AccessRuleForm, self).is_valid(*args, **kwargs)

class ScheduleRuleForm(ModelForm):
    class Meta:
        model = ScheduleRule
        exclude = ('last_run', 'report', 'hidden', 'config', 'created_at')
        widgets = {
            'schedule_type': forms.RadioSelect()
                }
