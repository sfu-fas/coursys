from courselib.auth import requires_role, ForbiddenResponse, NotFoundResponse
from coredata.models import Person
from grad.models import SavedSearch
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

@requires_role("GRAD", get_only=["GRPD"])
def delete_savedsearch(request):
    current_user = Person.objects.get(userid=request.user.username)
    if request.method != 'POST':
        return ForbiddenResponse(request)
    savedsearches = SavedSearch.objects.filter(
                person=request.POST['person'], 
                query=request.POST['query'])
    if not savedsearches:
        return NotFoundResponse(request, "This Saved Search doesn't exist.")
    savedsearch = savedsearches[0]
    if current_user != savedsearch.person:
        return ForbiddenResponse(request, "You cannot delete this Saved Search.")
    savedsearch.delete()
    messages.add_message(request, messages.SUCCESS, "Saved Search '%s' was successfully deleted." % savedsearch.name())
    return HttpResponseRedirect(reverse('grad:index'))
