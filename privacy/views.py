from django.shortcuts import render
from django.contrib import messages
from .forms import PrivacyForm
from courselib.auth import HttpResponseRedirect, requires_role
from coredata.models import Person
from .models import set_privacy_signed, PRIVACY_VERSION

def privacy(request):
    """
    View & sign the privacy statement.
    """
    try:
        you = Person.objects.get(userid=request.user.username)
    except Person.DoesNotExist:
        return HttpResponseRedirect("/")
    
    next_page = '/'
    if 'next' in request.GET:
        next_page = request.GET['next']
    
    privacy_date = ""
    if 'privacy_date' in you.config:
        privacy_date = you.config['privacy_date']
    privacy_version = ""
    if 'privacy_version' in you.config:
        privacy_version = you.config['privacy_version']
    
    good_to_go = False
    if privacy_version == PRIVACY_VERSION:
        good_to_go = True

    if request.POST:
        form = PrivacyForm(request.POST)
        if form.is_valid():
            set_privacy_signed(you)
            messages.add_message(request, messages.SUCCESS, 'Privacy agreement recorded. Thank you.')
            return HttpResponseRedirect(next_page)
    else:
        form = PrivacyForm()
    return render(request, 'privacy/privacy.html', {
        'form': form,
        'privacy_date': privacy_date,
        'good_to_go': good_to_go})
