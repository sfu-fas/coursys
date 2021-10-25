from logging import Logger
from coredata.models import Person
from django.http import HttpResponseRedirect,  HttpResponse
from django.urls import reverse
from courselib.auth import requires_role, ForbiddenResponse
from grad.forms import FinanceReportForm
from grad.models import STATUS_ACTIVE, GradStudent, Promise
from django.shortcuts import render, get_object_or_404
from coredata.models import Semester
import datetime
import csv
from grad.templatetags.getattribute import getattribute

@requires_role("GRAD")
def financials_report(request):
    form = FinanceReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
            finrpt = form.data['finreport']
            grads = _financials_report_promise(request.units, finrpt)    
                        
            context = {                   
                   'form':form,
                   'grads': grads,
                   'querystr': finrpt
                   }
    else:    
        if 'csv' in request.GET:            
            end_date = datetime.date.today()
            start_date = datetime.date(end_date.year, 1, 1)
            filename = 'financials_report_{}-{}.csv'.format(start_date.isoformat(), end_date.isoformat())            
            grads = _financials_report_promise(request.units, request.GET['finrpt'])

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            _generate_csv(request, response, grads)
            return response
        if 'excel' in request.GET:            
            end_date = datetime.date.today()
            start_date = datetime.date(end_date.year, 1, 1)
            filename = 'financials_report_{}-{}.xls'.format(start_date.isoformat(), end_date.isoformat()) 
            grads = _financials_report_promise(request.units, request.GET['finrpt'])

            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'inline; filename="{}"'.format(filename)
            _generate_excel(request, response, grads, request.GET['finrpt'])
            return response                    
        else:
            context = {                   
                   'form':form,
                   'querystr': ''
                   }
    
    return render(request, 'grad/financials_report.html', context)


def _financials_report_promise(units, finrpt):    
    if finrpt == 'phd':
        grads = GradStudent.objects.filter(program__unit__in=units).filter(current_status__in=STATUS_ACTIVE).filter(program__slug="phd").order_by("id")
    if finrpt == 'msc':
        grads = GradStudent.objects.filter(program__unit__in=units).filter(current_status__in=STATUS_ACTIVE).filter(program__slug__startswith="msc").order_by("id")
    if finrpt == 'all':
        grads = GradStudent.objects.filter(program__unit__in=units).filter(current_status__in=STATUS_ACTIVE).order_by("id")
    
    return grads

@requires_role("GRAD")
def _generate_csv(request, response, grads):
    writer = csv.writer(response) 
    writer.writerow([        
        'Employee ID',
        'Last Name',
        'First Name',
        'User',        
        'Program',
        'Supervisor(s)',
        'Current Status',
        'Start term',        
        'Promise Yr 1',
        'Promise Yr 2',
        'Promise Yr 3',
        'Promise Yr 4',
        'Promise (Other years)',
        'Total Promises Fund',
        'Received Yr 1',
        'Received Yr 2',
        'Received Yr 3',
        'Received Yr 4', 
        'Received (Other years)',    
        'Total Received',   
        'Difference Yr 1',
        'Difference Yr 2',
        'Difference Yr 3',
        'Difference Yr 4',   
        'Difference (Other years)', 
        'Total Difference'           
    ])


    for g in grads:
         writer.writerow([
            g.person.emplid,
            g.person.last_name,
            g.person.first_name,
            g.person.userid,
            g.program.label,
            getattribute(g, 'senior_supervisors'),
            g.current_status,
            g.start_semester.label(),
            g.get_year1_promise_amount(),
            g.get_year2_promise_amount(),
            g.get_year3_promise_amount(),
            g.get_year4_promise_amount(),
            g.get_otheryear_promise_amount(),
            g.get_total_promise_amount(),
            g.get_year1_received(),
            g.get_year2_received(),
            g.get_year3_received(),
            g.get_year4_received(),
            g.get_otheryear_received(),
            g.get_total_received(),
            g.get_year1_received()-g.get_year1_promise_amount(),
            g.get_year2_received()-g.get_year2_promise_amount(),
            g.get_year3_received()-g.get_year3_promise_amount(),
            g.get_year4_received()-g.get_year4_promise_amount(),
            g.get_otheryear_received()-g.get_otheryear_promise_amount(),
            g.get_total_received()-g.get_total_promise_amount()
        ]) 


@requires_role("GRAD")
def _generate_excel(request, response, grads, finrpt):
    end_date = datetime.date.today()
    start_date = datetime.date(end_date.year, 1, 1)

    import xlwt
    book = xlwt.Workbook(encoding='utf-8')
    sheet = book.add_sheet('Active '+finrpt)
    hdrstyle = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour grey25; align: horiz centre')
    highlightstyle = xlwt.easyxf('pattern: pattern solid, fore_colour yellow; ')
    boldhighlightstyle = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour yellow; ')
    boldstyle = xlwt.easyxf('font: bold on;')

    # header row
    sheet.write(0, 0, 'Financial Summary Report (Active '+finrpt+')' , xlwt.easyxf('font: bold on, height 220'))
    sheet.row(0).height = 400
    sheet.write(1, 1, 'Employee ID', hdrstyle)
    sheet.write(1, 2, 'Last Name', hdrstyle)
    sheet.write(1, 3, 'First Name', hdrstyle)
    sheet.write(1, 4, 'User', hdrstyle)
    sheet.write(1, 5, 'Program', hdrstyle)
    sheet.write(1, 6, 'Supervisor(s)', hdrstyle)
    sheet.write(1, 7, 'Current Status', hdrstyle)
    sheet.write(1, 8, 'Start term', hdrstyle)
    sheet.write(1, 9, 'Promise Yr 1', hdrstyle)
    sheet.write(1, 10, 'Promise Yr 2', hdrstyle)
    sheet.write(1, 11, 'Promise Yr 3', hdrstyle)
    sheet.write(1, 12, 'Promise Yr 4', hdrstyle)
    sheet.write(1, 13, 'Promise (Other years)', hdrstyle)
    sheet.write(1, 14, 'Total Promises Fund', hdrstyle)
    sheet.write(1, 15, 'Received Yr 1', hdrstyle)
    sheet.write(1, 16, 'Received Yr 2', hdrstyle)
    sheet.write(1, 17, 'Received Yr 3', hdrstyle)
    sheet.write(1, 18, 'Received Yr 4', hdrstyle)
    sheet.write(1, 19, 'Received (Other years)', hdrstyle)
    sheet.write(1, 20, 'Total Received',  hdrstyle)  
    sheet.write(1, 21, 'Difference Yr 1', hdrstyle)
    sheet.write(1, 22, 'Difference Yr 2', hdrstyle)
    sheet.write(1, 23, 'Difference Yr 3', hdrstyle)
    sheet.write(1, 24, 'Difference Yr 4',  hdrstyle)   
    sheet.write(1, 25, 'Difference (Other years)',  hdrstyle)
    sheet.write(1, 26, 'Total Difference', hdrstyle)    

    # data rows
    for i,g in enumerate(grads):
        
        sheet.write(i+2, 1, g.person.emplid)
        sheet.write(i+2, 2, g.person.last_name)
        sheet.write(i+2, 3, g.person.first_name)
        sheet.write(i+2, 4, g.person.userid)
        sheet.write(i+2, 5, g.program.label)
        sheet.write(i+2, 6, getattribute(g, 'senior_supervisors'))
        sheet.write(i+2, 7, g.current_status)
        sheet.write(i+2, 8, g.start_semester.label())
        sheet.write(i+2, 9, g.get_year1_promise_amount())
        sheet.write(i+2, 10, g.get_year2_promise_amount())
        sheet.write(i+2, 11, g.get_year3_promise_amount())
        sheet.write(i+2, 12, g.get_year4_promise_amount())
        sheet.write(i+2, 13, g.get_otheryear_promise_amount())
        sheet.write(i+2, 14, g.get_total_promise_amount(), boldstyle)
        sheet.write(i+2, 15, g.get_year1_received())
        sheet.write(i+2, 16, g.get_year2_received())
        sheet.write(i+2, 17, g.get_year3_received())
        sheet.write(i+2, 18, g.get_year4_received())
        sheet.write(i+2, 19, g.get_otheryear_received())
        sheet.write(i+2, 20, g.get_total_received(), boldstyle)
        diff1 =  g.get_year1_received()-g.get_year1_promise_amount()
        diff2 =  g.get_year2_received()-g.get_year2_promise_amount()
        diff3 =  g.get_year3_received()-g.get_year3_promise_amount()
        diff4 =  g.get_year4_received()-g.get_year4_promise_amount()
        diff5 =  g.get_otheryear_received()-g.get_otheryear_promise_amount()
        diffttl =  g.get_total_received()-g.get_total_promise_amount()
        if diff1 < -0.01:
            sheet.write(i+2, 21, diff1, highlightstyle)
        else:
            sheet.write(i+2, 21, diff1)
        if diff2 < -0.01:
            sheet.write(i+2, 22, diff2, highlightstyle)
        else:
            sheet.write(i+2, 22, diff2)   
        if diff3 < -0.01:
            sheet.write(i+2, 23, diff3, highlightstyle)
        else:
            sheet.write(i+2, 23, diff3)
        if diff4 < -0.01:
            sheet.write(i+2, 24, diff4, highlightstyle)
        else:
            sheet.write(i+2, 24, diff4)
        if diff5 < -0.01:
            sheet.write(i+2, 25, diff5, boldhighlightstyle)
        else:
            sheet.write(i+2, 25, diff5, boldstyle)
        if diffttl < -0.01:
            sheet.write(i+2, 26, diffttl, boldhighlightstyle)
        else:
            sheet.write(i+2, 26, diffttl, boldstyle)            


    count = len(grads)
    sheet.write(count+4, 0, 'Number of students: %i' % (count))
    sheet.write(count+5, 0, 'Report generated: %s' % (datetime.datetime.now()))
    
    book.save(response)
