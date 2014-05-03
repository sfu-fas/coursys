from django.shortcuts import render
from forms import PrivacyForm
from courselib.auth import HttpResponseRedirect, requires_role
from coredata.models import ROLE_CHOICES, Person
import datetime

PRIVACY_VERSION = 1;

# Who has to sign the Privacy statement? Anybody with a role. 
RELEVANT_ROLES = [role for role, description in ROLE_CHOICES if role != "NONE"]

@requires_role(RELEVANT_ROLES)
def privacy(request, return_to="/"):
    """
    View & sign the privacy statement.
    """
    you = Person.objects.get(userid=request.user.username)

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
            you.config["privacy_signed"] = True
            you.config["privacy_date"] = datetime.date.today()
            you.config["privacy_version"] = PRIVACY_VERSION 
            you.save()
            return HttpResponseRedirect(return_to)
    else:
        form = PrivacyForm()
    return render(request, 'privacy/privacy.html', {
        'form': form,
        'privacy_date': privacy_date,
        'good_to_go': good_to_go})
