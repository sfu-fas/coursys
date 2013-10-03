from django import forms
from django.forms.models import ModelForm
from models import Report, HardcodedReport, AccessRule, ScheduleRule
from django.template import Template, TemplateSyntaxError


class ReportForm(ModelForm):
    class Meta:
        model = Report
        exclude = ('config', 'created_at', 'hidden', 'last_run')

class HardcodedReportForm(ModelForm):
    class Meta:
        model = HardcodedReport
        exclude = ('report', 'hidden', 'config', 'created_at') 
