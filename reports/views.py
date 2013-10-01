from models import Report
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.template import Template, Context
import datetime

def view_reports(request):
    reports = Report.objects.filter(hidden=False)
    return render(request, 'reports/view_reports.html', {'reports':reports})
