from django.urls import reverse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from coredata.models import Person, Role
import datetime

PRIVACY_VERSION = 1
PRIVACY_DA_VERSION = 1

# Who has to sign the Privacy statement?
RELEVANT_ROLES = ['ADVS', 'ADMN', 'TAAD', 'GRAD', 'GRPD', 'FUND', 'FDRE', 'FDMA']


def set_privacy_signed(person):
    person.config["privacy_signed"] = True
    person.config["privacy_date"] = datetime.date.today()
    person.config["privacy_version"] = PRIVACY_VERSION 
    person.save()


def needs_privacy_signature(request, only_relevant_roles=False):
    """
    Decide if the user needs to see the privacy agreement.

    only_relevant_roles will show the user the agreement only if they have a Role that needs to agree: used in the
    generic @requires_role decorator. Default behaviour is if we called this, then they need to agree.
    """
    try:
        you = Person.objects.get(userid=request.user.username)
    except Person.DoesNotExist:
        return False # non-Person can't have a role to worry about

    if 'privacy_signed' in you.config and you.config['privacy_signed'] and 'privacy_version' in you.config and \
            you.config['privacy_version'] == PRIVACY_VERSION:
        return False

    if only_relevant_roles:
        roles = Role.objects_fresh.filter(person__userid=request.user.username, role__in=RELEVANT_ROLES)
        return roles.exists()
    else:
        return True


def privacy_redirect(request):
    """
    Build the redirect response to give a user that needs to agree
    """
    privacy_url = reverse('config:privacy')
    path = '%s?%s=%s' % (privacy_url, REDIRECT_FIELD_NAME,
                         urlquote(request.get_full_path()))
    return HttpResponseRedirect(path)


def set_privacy_da_signed(person):
    person.config["privacy_da_signed"] = True
    person.config["privacy_da_date"] = datetime.date.today()
    person.config["privacy_da_version"] = PRIVACY_DA_VERSION
    person.save()


def needs_privacy_signature_da(request):
    # A different version that we must also show only to Department Admins.
    try:
        you = Person.objects.get(userid=request.user.username)
    except Person.DoesNotExist:
        return False # non-Person can't have a role to worry about

    if 'privacy_da_signed' in you.config and you.config['privacy_da_signed'] and 'privacy_da_version' in you.config and \
            you.config['privacy_da_version'] == PRIVACY_DA_VERSION:
        return False

    roles = Role.objects_fresh.filter(person__userid=request.user.username, role='ADMN')
    return roles.exists()


def privacy_da_redirect(request):
    """
    Build the redirect response to give a user that needs to agree
    """
    privacy_url = reverse('config:privacy_da')
    path = '%s?%s=%s' % (privacy_url, REDIRECT_FIELD_NAME,
                         urlquote(request.get_full_path()))
    return HttpResponseRedirect(path)
