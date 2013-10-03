from models import Report, HardcodedReport
from forms import ReportForm, HardcodedReportForm
from courselib.auth import requires_role, HttpResponseRedirect, ForbiddenResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.template import Template, Context
from django.forms.util import ErrorList
import datetime

def view_reports(request):
    reports = Report.objects.filter(hidden=False)
    return render(request, 'reports/view_reports.html', {'reports':reports})

def new_report(request):     
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.save()
            messages.success(request, "Created new report: %s." % f.name)
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':f.slug}))
    else:
        form = ReportForm()

    return render(request, 'reports/new_report.html', {'form': form })

def view_report(request, report):
    report = get_object_or_404(Report, slug=report) 
    
    components = HardcodedReport.objects.filter(report=report)

    return render(request, 'reports/view_report.html', {'report':report, 'components':components})

def new_component(request, report):
    report = get_object_or_404(Report, slug=report) 
    file_locations = [component.file_location for component in HardcodedReport.objects.filter(report=report)]

    if request.method == 'POST':
        form = HardcodedReportForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            if f.file_location in file_locations: 
                messages.error(request, 'A ReportComponent with this file already exists.' )
            else: 
                f.report = report
                f.created_by = request.user.username
                f.save()
                messages.success(request, "Created new report component: %s." % f.file_location)
                return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = HardcodedReportForm()

    return render(request, 'reports/new_component.html', {'form': form, 'report': report })

def delete_component(request, report, component_id):
    report = get_object_or_404(Report, slug=report)
    component = get_object_or_404(HardcodedReport, id=int(component_id))
    
    component.delete()
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))

def run(request, report):
    report = get_object_or_404(Report, slug=report)
    report.run()
    messages.success(request, "Thing happened.")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
