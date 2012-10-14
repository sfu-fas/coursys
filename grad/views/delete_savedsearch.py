from courselib.auth import requires_role, ForbiddenResponse, NotFoundResponse
from coredata.models import Person
from grad.models import SavedSearch
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

@requires_role("GRAD")
def delete_savedsearch(request):
    current_user = Person.objects.get(userid=request.user.username)
    if request.method != 'POST':
        return ForbiddenResponse(request)
    try:
        savedsearch = SavedSearch.objects.get(
                person=request.POST['person'], 
                query=request.POST['query'])
    except SavedSearch.DoesNotExist:
        return NotFoundResponse(request, u"This Saved Search doesn't exist.")
    if current_user != savedsearch.person:
        return ForbiddenResponse(request, u"You cannot delete this Saved Search.")
    savedsearch.delete()
    messages.add_message(request, messages.SUCCESS, u"Saved Search '%s' was successfully deleted." % savedsearch.name())
    return HttpResponseRedirect(reverse('grad.views.index'))
