from models import Report, HardcodedReport, Result, Run, RunLine, Query
from forms import ReportForm, HardcodedReportForm, QueryForm
from courselib.auth import requires_role, HttpResponseRedirect, ForbiddenResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.template import Template, Context
from django.forms.util import ErrorList
import unicodecsv as csv
import datetime

@requires_role('REPR')
def view_reports(request):
    reports = Report.objects.filter(hidden=False)
    return render(request, 'reports/view_reports.html', {'reports':reports})

@requires_role('REPR')
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

@requires_role('REPR')
def view_report(request, report):
    report = get_object_or_404(Report, slug=report) 
    
    components = HardcodedReport.objects.filter(report=report)
    queries = Query.objects.filter(report=report)
    runs = Run.objects.filter(report=report).order_by("created_at")

    return render(request, 'reports/view_report.html', {'report':report, 
                                                        'queries':queries, 
                                                        'runs':runs, 
                                                        'components':components})

@requires_role('REPR')
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

@requires_role('REPR')
def delete_component(request, report, component_id):
    report = get_object_or_404(Report, slug=report)
    component = get_object_or_404(HardcodedReport, id=int(component_id))
    
    component.delete()
    messages.success(request, "Deleted component")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))

@requires_role('REPR')
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

@requires_role('REPR')
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
    

@requires_role('REPR')
def delete_query(request, report, query_id):
    report = get_object_or_404(Report, slug=report)
    query = get_object_or_404(Query, id=int(query_id))
    
    query.delete()
    messages.success(request, "Deleted query")
    return HttpResponseRedirect(reverse('reports.views.view_report', kwargs={'report':report.slug}))
    

@requires_role('REPR')
def run(request, report):
    """ Actually execute the report. """
    report = get_object_or_404(Report, slug=report)
    run = report.run()
    if( run.success ):
        messages.success(request, "Run Succeeded!")
    else: 
        messages.error(request, "Run Failed!")
    return HttpResponseRedirect(reverse('reports.views.view_run', kwargs={'report':report.slug, 'run':run.slug}))

@requires_role('REPR')
def view_run(request, report, run):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    runlines = run.getLines()
    results = Result.objects.filter( run=run )
    
    return render(request, 'reports/view_run.html', {'report':report, 'run': run, 'runlines':runlines, 'results':results})

@requires_role('REPR')
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

@requires_role('REPR')
def view_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    # TODO: replace with slug
    result = get_object_or_404(Result, id=result)
    
    return render(request, 'reports/view_result.html', {'report':report, 'run': run, 'result':result})

@requires_role('REPR')
def csv_result(request, report, run, result):
    run = get_object_or_404(Run, slug=run)
    report = run.report
    result = get_object_or_404(Result, id=result)

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
