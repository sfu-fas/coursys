from models import Report, HardcodedReport, Result, Run, RunLine, \
                    Query, AccessRule, ScheduleRule
from forms import ReportForm, HardcodedReportForm, QueryForm, \
                    AccessRuleForm, ScheduleRuleForm
from alerts.models import AlertType
from alerts.forms import AlertTypeForm
from courselib.auth import requires_role, has_role, HttpResponseRedirect, \
                    ForbiddenResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.template import Template, Context
from django.forms.util import ErrorList
from django.conf import settings
import unicodecsv as csv
import datetime
import shutil


def view_reports(request):
    if has_role('SYSA', request):
        reports = Report.objects.filter(hidden=False)
        readonly = False
    else:
        readonly = True
        access_rules = AccessRule.objects.filter(person__userid=request.user.username)
        reports = [rule.report for rule in access_rules if rule.report.hidden == False]

    return render(request, 'reports/view_reports.html', {'readonly':readonly, 'reports':reports})


@requires_role('SYSA')
def new_report(request):     
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.save()
            messages.success(request, "Created new report: %s." % f.name)
            return HttpResponseRedirect(reverse('reports.views.view_report', 
                                                    kwargs={'report':f.slug}))
    else:
        form = ReportForm()

    return render(request, 'reports/new_report.html', {'form': form })


def _has_access(request, report):
    return has_role('SYSA', request) or AccessRule.objects.get(report=report, person__userid=request.user.username)


def view_report(request, report):
    report = get_object_or_404(Report, slug=report) 
    readonly = True
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)
    if has_role('SYSA', request):
        readonly = False
  
    access_rules = AccessRule.objects.filter(report=report)
    schedule_rules = ScheduleRule.objects.filter(report=report)
    components = HardcodedReport.objects.filter(report=report)
    queries = Query.objects.filter(report=report)
    runs = Run.objects.filter(report=report).order_by("created_at")

    return render(request, 'reports/view_report.html', {'readonly':readonly,
                                                        'report':report,
                                                        'is_scheduled_to_run':report.is_scheduled_to_run(),
                                                        'queries':queries, 
                                                        'schedule_rules':schedule_rules,
                                                        'access_rules':access_rules,
                                                        'runs':runs, 
                                                        'components':components})

def console(request, report):
    report = get_object_or_404(Report, slug=report) 
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)

    runs = Run.objects.filter(report=report).order_by("-created_at")
    if len(runs) == 0:
        return ""
    
    last_run = runs[0]
    runlines = last_run.getLines()
    log_lines = [line[1] for line in runlines]

    return HttpResponse("\n".join(log_lines), content_type="text/plain")


@requires_role('SYSA')
def new_access_rule(request, report):
    report = get_object_or_404(Report, slug=report) 

    if request.method == 'POST':
        form = AccessRuleForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.report = report
            f.save()
            messages.success(request, "Created new access rule:  %s." % str(f.person) )
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = AccessRuleForm()

    return render(request, 'reports/new_access_rule.html', {'form': form, 'report': report })


@requires_role('SYSA')
def delete_access_rule(request, report, access_rule_id):
    report = get_object_or_404(Report, slug=report)
    access_rule = get_object_or_404(AccessRule, id=int(access_rule_id))

    access_rule.delete()
    messages.success(request, "Deleted access rule")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


@requires_role('SYSA')
def new_schedule_rule(request, report):
    report = get_object_or_404(Report, slug=report)

    if request.method == 'POST':
        form = ScheduleRuleForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.report = report
            f.save()
            messages.success(request, "Created new schedule:  %s." % str(f.next_run) )
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = ScheduleRuleForm()

    return render(request, 'reports/new_schedule_rule.html', {'form': form, 'report': report })


@requires_role('SYSA')
def delete_schedule_rule(request, report, schedule_rule_id):
    report = get_object_or_404(Report, slug=report)
    schedule_rule = get_object_or_404(ScheduleRule, id=int(schedule_rule_id))

    schedule_rule.delete()
    messages.success(request, "Deleted schedule rule")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


@requires_role('SYSA')
def new_component(request, report):
    report = get_object_or_404(Report, slug=report) 
    file_locations = [component.file_location for component in 
                            HardcodedReport.objects.filter(report=report)]

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


@requires_role('SYSA')
def delete_component(request, report, component_id):
    report = get_object_or_404(Report, slug=report)
    component = get_object_or_404(HardcodedReport, id=int(component_id))
    
    component.delete()
    messages.success(request, "Deleted component")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


@requires_role('SYSA')
def new_query(request, report):
    report = get_object_or_404(Report, slug=report) 

    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.report = report
            f.created_by = request.user.username
            f.save()
            messages.success(request, "Created new report query: %s" % f.query)
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = QueryForm()

    return render(request, 'reports/new_query.html', {'form': form, 'report': report })


@requires_role('SYSA')
def edit_query(request, report, query_id):
    report = get_object_or_404(Report, slug=report)
    query = get_object_or_404(Query, id=int(query_id))

    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.report = report
            f.created_by = request.user.username
            f.save()
            query.delete()
            messages.success(request, "Edited query: %s" % f.query)
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = QueryForm(instance=query)

    return render(request, 'reports/edit_query.html', {'form': form, 'report': report, 'query_id':query_id })
    

@requires_role('SYSA')
def delete_query(request, report, query_id):
    report = get_object_or_404(Report, slug=report)
    query = get_object_or_404(Query, id=int(query_id))
    
    query.delete()
    messages.success(request, "Deleted query")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


def run(request, report):
    """ Actually execute the report. """
    report = get_object_or_404(Report, slug=report)
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)
   
    # TODO: this really shouldn't be a synchronous operation. 
    runs = report.run()
    if len(runs) > 0: 
        for run in runs: 
            if( run.success ):
                messages.success(request, "Run Succeeded!")
            else: 
                messages.error(request, "Run Failed!")
        run = runs[0]
        shutil.rmtree(settings.REPORT_CACHE_LOCATION)
        return HttpResponseRedirect(reverse('reports.views.view_run', kwargs={'report':report.slug, 'run':run.slug}))
    else:
        messages.error(request, "You haven't added any queries or reports to run, yet!")
        return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


def view_run(request, report, run):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)
    
    runlines = run.getLines()
    results = Result.objects.filter( run=run )
    
    return render(request, 'reports/view_run.html', {'report':report, 'run': run, 'runlines':runlines, 'results':results})


@requires_role('SYSA')
def delete_run(request, report, run):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    runlines = RunLine.objects.filter( run=run )
    results = Result.objects.filter( run=run )

    for result in results: 
        result.delete()
    for line in runlines:
        line.delete()
    run.delete()

    messages.success(request, "Run Deleted!")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))


def view_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)
    
    result = get_object_or_404(Result, slug=result)
    
    return render(request, 'reports/view_result.html', {'report':report, 'run': run, 'result':result})


def csv_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    
    if not _has_access(request, report):
        return ForbiddenResponse(request)
    
    result = get_object_or_404(Result, slug=result)

    print result.autoslug()
    filename = str(report.slug) + '-' + result.autoslug() + '.csv'
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'inline; filename=%s'% filename
    csvWriter = csv.writer(response)

    table = result.table_rendered()
    csvWriter.writerow(table.headers)
    for row in table.rows: 
        csvWriter.writerow(row)
    
    return response

@requires_role('SYSA')
def new_alert(request, report):
    report = get_object_or_404(Report, slug=report)

    if request.method == 'POST':
        form = AlertTypeForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.save()
            messages.success(request, "Created new alert type:  %s." % str(f.code) )
            report.alert = f
            report.save()
            return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    else:
        form = AlertTypeForm()

    return render(request, 'reports/new_alert.html', {'form': form, 'report': report })
