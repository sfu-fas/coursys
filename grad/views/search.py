from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, SavedSearch
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import SearchForm, SaveSearchForm, COLUMN_CHOICES
from django.core.urlresolvers import reverse
from coredata.models import Person
import unicodecsv as csv
import copy
import operator


def _get_cleaned_get(request):
    """
        Returns a GET request with every parameter that has no values removed. 
    """
    cleaned_get = copy.copy(request.GET)
    for parameter, parameter_values in request.GET.iterlists():
        if len(filter(lambda x:len(x) > 0, parameter_values)) == 0:
            del cleaned_get[parameter]
    return cleaned_get

@requires_role("GRAD")
def search(request):
    # Possible TODOs for search:
    # TODO: make groups of search fields collapsible
        # use field lists like SearchForm.semester_range_fields to organize the fields
        # into groups, like Dates, Student Status, Academics, Financials and Personal Details
        # and put the groups into separate divs, with headers, and use jquery.collapsible
        # on each of the groups
        # also this should allow the user to replace the loaded savedsearch with a new one
    # TODO: allow loading a saved search into the search form
        # make a new view for this purpose, or separate the results view into its own
        # just 'copy' (aka refactor by splitting up and follow DRY) this search view to just 
        # load the searchform with the savedsearch query as initial
    current_user = Person.objects.get(userid=request.user.username)
    query_string = request.META.get('QUERY_STRING','')
    try:
        savedsearch = SavedSearch.objects.get(person=current_user, query=query_string)
    except SavedSearch.DoesNotExist:
        savedsearch = None
    if savedsearch is None:
        if len(request.GET) > 0:
            cleaned_get = _get_cleaned_get(request)
            if len(cleaned_get) < len(request.GET):
                return HttpResponseRedirect(reverse(search) + u'?' + cleaned_get.urlencode())
        try:
            savedsearch = SavedSearch.objects.get(person=current_user, query=query_string)
        except SavedSearch.DoesNotExist:
            savedsearch = None
    
    form = SearchForm() if len(request.GET) == 0 else SearchForm(request.GET)
    
    if form.is_valid():
        query = form.get_query()
        grads = GradStudent.objects.filter(program__unit__in=request.units).filter(query).distinct()
        grads = filter(form.secondary_filter(), grads)
        
        if savedsearch is not None:
            saveform = SaveSearchForm(instance=savedsearch)
        else:
            saveform = SaveSearchForm(initial={'person':current_user, 'query':query_string})
        
        columns = form.cleaned_data['columns']
        # Here, we're using a nested list comprehension to convert column ids into column names - 
        #  for example 'person.first_name' into 'First Name' - using the COLUMN_CHOICES table provided in forms.py
        human_readable_column_headers = [[v[1] for i,v in enumerate(COLUMN_CHOICES) if v[0] == column][0] for column in columns]
        
        if 'csv' in request.GET:
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=grad_search.csv'
            writer = csv.writer( response) 
            
            writer.writerow( human_readable_column_headers )
            
            for grad in grads:
                row = []
                for column in columns:
                    # operator.attrgetter allows you to get nested attributes from a class, using a string 
                    # example:  print operator.attrgetter("person.first_name")(grad) 
                    # >> "Abdul" 
                    row.append( operator.attrgetter(column)(grad) )
                writer.writerow( row ) 
            return response
        
        context = {
                   'grads': grads,
                   'human_readable_column_headers': human_readable_column_headers,
                   'columns': columns,
                   'saveform' : saveform,
                   'csv_link' : request.get_full_path() + "&csv=yes_please"
                   }
        return render(request, 'grad/search_results.html', context)
    else:
        savedsearches = SavedSearch.objects.filter(person__in=(current_user,None))
        page_title = 'Graduate Student Advanced Search'
        context = {
                   'savedsearches' : savedsearches,
                   'page_title' : page_title,
                   'form':form,
                   'savedsearch' : savedsearch 
                   # a non-None savedsearch here means that somehow, an invalid search got saved
                   # the template gives the user the option to delete it
                   }
        return render(request, 'grad/search.html', context)
