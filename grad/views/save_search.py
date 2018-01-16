from courselib.auth import requires_role
from grad.models import SavedSearch
from django.http import HttpResponseRedirect
from grad.forms import SaveSearchForm
from django.contrib import messages
from coredata.models import Person
from django.core.urlresolvers import reverse

@requires_role("GRAD", get_only=["GRPD"])
def save_search(request):
    current_user = Person.objects.get(userid=request.user.username)
    saveform = SaveSearchForm(request.POST)
    
    if saveform.is_valid():
        name = saveform.cleaned_data['name']
        existing_ss = SavedSearch.objects.filter(person=saveform.data['person'])
        existing_ss = [ss for ss in existing_ss if ss.name()==name]
        for ss in existing_ss:
            ss.delete()
        
        ss = saveform.save(commit=False)
        ss.person = current_user
        ss.save()
        messages.add_message(request, messages.SUCCESS, 'Search Saved as "%s".' % (name))
        return HttpResponseRedirect(reverse('grad:index'))
    else:
        messages.add_message(request, messages.ERROR, saveform.errors.as_text())
        if True or 'query' in saveform.data:
            return HttpResponseRedirect(reverse('grad:search') + '?' + saveform.data['query'])
        else:
            return HttpResponseRedirect(reverse('grad:search'))
