from courselib.auth import requires_role
from grad.models import SavedSearch
from django.http import HttpResponseRedirect
from grad.forms import SaveSearchForm
from django.contrib import messages
from coredata.models import Person
from django.core.urlresolvers import reverse
from search import search

@requires_role("GRAD")
def save_search(request):
    current_user = Person.objects.get(userid=request.user.username)
    saveform = SaveSearchForm(request.POST)
    try:
        saveform.instance = SavedSearch.objects.get(
                person=saveform.data['person'], 
                query=saveform.data['query'])
    except SavedSearch.DoesNotExist:
        saveform.instance = SavedSearch(person=current_user)
    if saveform.is_valid():
        saveform.save()
        return HttpResponseRedirect(reverse(search))
    else:
        messages.add_message(request, messages.ERROR, saveform.errors.as_text())
        return HttpResponseRedirect(reverse(search) + u'?' + saveform.data['query'])
