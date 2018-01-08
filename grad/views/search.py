from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent, GradFlag, GradProgram, SavedSearch, GradRequirement, \
    ScholarshipType, Supervisor, STATUS_ACTIVE, STATUS_OBSOLETE, STATUS_CHOICES
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.safestring import mark_safe
from django.contrib import messages
from grad.forms import SearchForm, SaveSearchForm, COLUMN_CHOICES, COLUMN_WIDTHS
from django.core.urlresolvers import reverse
from coredata.models import Person
import unicodecsv as csv
import copy, datetime, json
from grad.templatetags.getattribute import getattribute
from dashboard.letters import card_req_forms, fasnet_forms

MAX_RESULTS = 1000

def _get_cleaned_get(request):
    """
        Returns a GET request with every parameter that has no values removed. 
    """
    cleaned_get = copy.copy(request.GET)
    for parameter, parameter_values in request.GET.iterlists():
        if len([x for x in parameter_values if len(x) > 0]) == 0:
            del cleaned_get[parameter]
    return cleaned_get

def _parse_sort(sortstr):
    """
    Decode the microformat for search order in URL.
    
    The format is "2a,15d" maps to datables aaSorting value [[2,'asc'], [15,'desc']]
    """
    res = []
    for col in sortstr.split(','):
        if not col:
            return None
        num = col[:-1]
        order = col[-1]
        try:
            num = int(num)
        except ValueError:
            return None
        if order == 'd':
            order = 'desc'
        elif order == 'a':
            order = 'asc'
        else:
            return None
        res.append([num, order])
    return mark_safe(json.dumps(res))


def _generate_csv(response, columns, headers, grads):
    writer = csv.writer(response)
    writer.writerow( headers )
    for grad in grads:
        row = []
        for column in columns:
            value = getattribute(grad, column, html=False)
            row.append(value)
        writer.writerow( row )


def _generate_excel(response, columns, headers, grads):
    import xlwt
    book = xlwt.Workbook(encoding='utf-8')
    sheet = book.add_sheet('Search Results')
    hdrstyle = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour grey25; align: horiz centre')
    evenstyle = xlwt.easyxf('pattern: back_colour gray40')
    oddstyle = xlwt.easyxf('pattern: pattern sparse_dots, fore_colour grey25')
    
    # header row
    sheet.write(0, 0, 'Graduate Student Search Results', xlwt.easyxf('font: bold on, height 320'))
    sheet.row(0).height = 400
    for i,hdr in enumerate(headers):
        sheet.write(1, i, hdr, hdrstyle)
    
    # data rows
    for i,grad in enumerate(grads):
        style = [oddstyle, evenstyle][i%2]
        for j,column in enumerate(columns):
            sheet.write(i+2, j, getattribute(grad, column, html=False), style)
    
    # set column widths
    for i,c in enumerate(columns):
        wid = COLUMN_WIDTHS[c]
        sheet.col(i).width = wid
    
    count = len(grads)
    sheet.write(count+4, 0, 'Number of students: %i' % (count))
    sheet.write(count+5, 0, 'Report generated: %s' % (datetime.datetime.now()))
    
    book.save(response)



@requires_role("GRAD", get_only=["GRPD"])
def search(request):
    current_user = Person.objects.get(userid=request.user.username)
    query_string = request.META.get('QUERY_STRING','')
    savedsearches = SavedSearch.objects.filter(person=current_user, query=query_string)
    if savedsearches:
        savedsearch = savedsearches[0]
    else:
        savedsearch = None

    form = SearchForm(initial={'student_status': STATUS_ACTIVE}) if len(request.GET) == 0 else SearchForm(request.GET)

    requirement_choices = [(r['series'], r['description']) for r in
            GradRequirement.objects.filter(program__unit__in=request.units, hidden=False)
            .order_by('description').values('series', 'description').distinct()]

    scholarshiptype_choices = [(st.id, st.name) for st in ScholarshipType.objects.filter(unit__in=request.units, hidden=False)]

    # If the user has the grad role for more than one unit, append the unit label to the name of the program so
    # they know which one they are looking at.
    if len(request.units) > 1:
        program_choices = [(gp.id, "%s - %s" % (gp.unit.label, gp.label)) for gp in
                           GradProgram.objects.filter(unit__in=request.units, hidden=False)]
    else:
        program_choices = [(gp.id, gp.label) for gp in GradProgram.objects.filter(unit__in=request.units, hidden=False)]

    status_choices = [(st,desc) for st,desc in STATUS_CHOICES if st not in STATUS_OBSOLETE] + [('', 'None')]

    supervisors = Supervisor.objects.filter(student__program__unit__in=request.units, supervisor_type='SEN',
                                            removed=False).select_related('supervisor')
    supervisors = set((s.supervisor for s in supervisors if s.supervisor))
    supervisors = list(supervisors)
    supervisors.sort()
    supervisor_choices = [(p.id, p.sortname()) for p in supervisors]

    grad_flags = GradFlag.objects.filter(unit__in=request.units)
    grad_flag_choices = [(g.id, g.label) for g in grad_flags]

    form.fields['requirements'].choices = requirement_choices
    form.fields['incomplete_requirements'].choices = requirement_choices
    form.fields['scholarshiptype'].choices = scholarshiptype_choices
    form.fields['program'].choices = program_choices
    form.fields['student_status'].choices = status_choices
    form.fields['supervisor'].choices = supervisor_choices
    form.fields['grad_flags'].choices = grad_flag_choices
    
    if 'sort' in request.GET:
        sort = _parse_sort(request.GET['sort'])
    else:
        sort = None;
    
    if 'edit_search' not in request.GET and form.is_valid():
        grads = form.search_results(request.units)

        overflow = False
        if len(grads) > MAX_RESULTS:
            grads = grads[:MAX_RESULTS]
            overflow = True
        
        if savedsearch is not None:
            saveform = SaveSearchForm(instance=savedsearch)
        else:
            saveform = SaveSearchForm(initial={'person':current_user, 'query':query_string})
        
        columns = form.cleaned_data['columns']
        # Here, we're using a nested list comprehension to convert column ids into column names - 
        #  for example 'person.first_name' into 'First Name' - using the COLUMN_CHOICES table provided in forms.py
        human_readable_column_headers = [[v[1] for _,v in enumerate(COLUMN_CHOICES) if v[0] == column][0] for column in columns]
        
        if 'csv' in request.GET:
            # CSV output
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'inline; filename="grad_search.csv"'
            _generate_csv(response, columns, human_readable_column_headers, grads)
            return response
        
        elif 'excel' in request.GET:
            # Excel output
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'inline; filename="grad_search.xls"'
            _generate_excel(response, columns, human_readable_column_headers, grads)
            return response
        
        elif 'cardforms' in request.GET:
            # access card requisition output
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="card_access.pdf"'
            card_req_forms(grads, response)
            return response
        
        elif 'fasnetforms' in request.GET:
            # access card requisition output
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="fasnet_access.pdf"'
            fasnet_forms(grads, response)
            return response
        
        if overflow:
            messages.warning(request, "Too many result found: limited to %i." % (MAX_RESULTS))

        context = {
                   'grads': grads,
                   'human_readable_column_headers': human_readable_column_headers,
                   'columns': columns,
                   'saveform' : saveform,
                   'query_string': query_string,
                   'sort': sort,
                   'uses_fasnet': any(u.uses_fasnet() for u in request.units),
                   }
        resp = render(request, 'grad/search_results.html', context)
        return resp
    else:
        #savedsearches = SavedSearch.objects.filter(person__in=(current_user,None))
        page_title = 'Graduate Student Advanced Search'
        context = {
                   #'savedsearches' : savedsearches,
                   'page_title' : page_title,
                   'form':form,
                   'savedsearch' : savedsearch,
                   # a non-None savedsearch here means that somehow, an invalid search got saved
                   # the template gives the user the option to delete it
                   }
        resp = render(request, 'grad/search.html', context)
        return resp
