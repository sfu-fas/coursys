from views import RELEVANT_ROLES
from coredata.models import Person, Role
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

def check_privacy_signature(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            you = Person.objects.get(userid=request.user.username)
        except Person.DoesNotExist:
            return view_func(request, *args, **kwargs)

        roles = Role.objects.filter(person__userid=request.user.username, 
                                    role__in=RELEVANT_ROLES)

        if 'privacy_signed' in you.config and you.config['privacy_signed']:
            return view_func(request, *args, **kwargs)
        elif len(roles) == 0:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse("privacy.views.privacy"))
    return wrapper
