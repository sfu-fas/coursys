from coredata.models import Person, Role
import datetime

PRIVACY_VERSION = 1

# Who has to sign the Privacy statement?
RELEVANT_ROLES = ['ADVS', 'ADMN', 'TAAD', 'GRAD', 'GRPD', 'FUND']

def set_privacy_signed(person):
    person.config["privacy_signed"] = True
    person.config["privacy_date"] = datetime.date.today()
    person.config["privacy_version"] = PRIVACY_VERSION 
    person.save()

def needs_privacy_signature(request):   
    try:
        you = Person.objects.get(userid=request.user.username)
    except Person.DoesNotExist:
        return False # non-Person can't have a role to worry about

    if 'privacy_signed' in you.config and you.config['privacy_signed']:
        return False

    roles = Role.objects.filter(person__userid=request.user.username, 
                                role__in=RELEVANT_ROLES)
    return roles.exists()
