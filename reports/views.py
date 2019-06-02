# Python
import json

# Django
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib import messages

# Third-Party
import csv

# Local
from privacy.models import needs_privacy_signature, privacy_redirect
from courselib.auth import requires_role, has_role, HttpResponseRedirect, \
                    ForbiddenResponse

# App
from .models import Report, HardcodedReport, Result, Run, RunLine, \
                    Query, AccessRule, ScheduleRule
from .forms import ReportForm, HardcodedReportForm, QueryForm, \
                    AccessRuleForm, ScheduleRuleForm
from .cache import clear_cache

def _has_access(request, report):
    try:
        return (has_role('SYSA', request) or
                AccessRule.objects.filter(report=report, person__userid=request.user.username).exists() or
                has_role('REPV', request)
                )
    except AccessRule.DoesNotExist:
        return False

def requires_report_access():
    """
    Decorator to check for being allowed access to the report
    """
    def actual_decorator(view_func):
        def can_access_report(request, report, **kwargs):
            rep = get_object_or_404(Report, slug=report)
            if not _has_access(request, rep):
                return ForbiddenResponse(request)
            if needs_privacy_signature(request):
                return privacy_redirect(request)

            request.report = rep # no need to re-fetch it later
            return view_func(request=request, report=report, **kwargs)

        return can_access_report

    return actual_decorator





def view_reports(request):
    if has_role('SYSA', request):
        reports = Report.objects.filter(hidden=False).order_by('name')
        readonly = False
    elif has_role('REPV', request):
        reports = Report.objects.filter(hidden=False).order_by('name')
        readonly = True
    else:
        readonly = True
        access_rules = AccessRule.objects.filter(person__userid=request.user.username).order_by('report__name')
        reports = [rule.report for rule in access_rules if not rule.report.hidden]

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
            return HttpResponseRedirect(reverse('reports:view_report',
                                                    kwargs={'report':f.slug}))
    else:
        form = ReportForm()

    return render(request, 'reports/new_report.html', {'form': form })



@requires_report_access()
def view_report(request, report):
    report = request.report
    readonly = True
    
    if has_role('SYSA', request):
        readonly = False
  
    access_rules = AccessRule.objects.filter(report=report)
    schedule_rules = ScheduleRule.objects.filter(report=report)
    components = HardcodedReport.objects.filter(report=report)
    queries = Query.objects.filter(report=report)
    runs = Run.objects.filter(report=report).order_by("-created_at")

    return render(request, 'reports/view_report.html', {'readonly':readonly,
                                                        'report':report,
                                                        'is_scheduled_to_run':report.is_scheduled_to_run(),
                                                        'queries':queries, 
                                                        'schedule_rules':schedule_rules,
                                                        'access_rules':access_rules,
                                                        'runs':runs, 
                                                        'components':components})

@requires_report_access()
def OFFconsole(request, report):
    report = request.report

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
            return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))
    else:
        form = AccessRuleForm()

    return render(request, 'reports/new_access_rule.html', {'form': form, 'report': report })


@requires_role('SYSA')
def delete_access_rule(request, report, access_rule_id):
    report = get_object_or_404(Report, slug=report)
    access_rule = get_object_or_404(AccessRule, id=int(access_rule_id))

    access_rule.delete()
    messages.success(request, "Deleted access rule")
    return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))


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
            return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))
    else:
        form = ScheduleRuleForm()

    return render(request, 'reports/new_schedule_rule.html', {'form': form, 'report': report })


@requires_role('SYSA')
def delete_schedule_rule(request, report, schedule_rule_id):
    report = get_object_or_404(Report, slug=report)
    schedule_rule = get_object_or_404(ScheduleRule, id=int(schedule_rule_id))

    schedule_rule.delete()
    messages.success(request, "Deleted schedule rule")
    return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))


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
                return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))
    else:
        form = HardcodedReportForm()

    return render(request, 'reports/new_component.html', {'form': form, 'report': report})


@requires_role('SYSA')
def delete_component(request, report, component_id):
    report = get_object_or_404(Report, slug=report)
    component = get_object_or_404(HardcodedReport, id=int(component_id))
    
    component.delete()
    messages.success(request, "Deleted component")
    return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))


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
            return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))
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
            return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))
    else:
        form = QueryForm(instance=query)

    return render(request, 'reports/edit_query.html', {'form': form, 'report': report, 'query_id':query_id })
    

@requires_role('SYSA')
def delete_query(request, report, query_id):
    report = get_object_or_404(Report, slug=report)
    query = get_object_or_404(Query, id=int(query_id))
    
    query.delete()
    messages.success(request, "Deleted query")
    return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))


@requires_report_access()
def run(request, report):
    """ Actually execute the report. """
    report = request.report

    task = report.enqueue(manual=True)
    return render(request, 'reports/running.html', {'report':report, 'task': task})


@requires_report_access()
def console(request, report):
    report = request.report

    data = {'done': True}
    runs = Run.objects.filter(report=report).order_by("-created_at")
    if len(runs) > 0:
        last_run = runs[0]
        runlines = last_run.getLines()
        log_lines = [line[1] for line in runlines]
        data['log'] = log_lines
        data['done'] = last_run.success
        if last_run.success:
            data['url'] = reverse('reports:view_run', kwargs={'report': report.slug, 'run': last_run.slug})
            clear_cache()

    return HttpResponse(json.dumps(data), content_type="application/json")


@requires_report_access()
def view_run(request, report, run):
    run = get_object_or_404(Run, slug=run, report__slug=report)
    report = run.report
    
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
    return HttpResponseRedirect(reverse('reports:view_report', kwargs={'report':report.slug}))


@requires_report_access()
def view_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run, report__slug=report)
    report = run.report
    result = get_object_or_404(Result, slug=result, run=run)
    
    return render(request, 'reports/view_result.html', {'report':report, 'run': run, 'result':result})


@requires_report_access()
def csv_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run, report__slug=report)
    report = run.report
    result = get_object_or_404(Result, slug=result, run=run)

    filename = str(report.slug) + '-' + result.autoslug() + '.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename=%s'% filename
    csvWriter = csv.writer(response)

    table = result.table_rendered()
    csvWriter.writerow(table.headers)
    for row in table.rows: 
        csvWriter.writerow(row)
    
    return response

