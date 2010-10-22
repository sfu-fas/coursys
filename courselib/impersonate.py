# modified from http://stackoverflow.com/questions/2242909/django-user-impersonation-by-admin

from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from courselib.auth import has_role
from log.models import LogEntry

class ImpersonateMiddleware(object):
    def process_request(self, request):
        if "__impersonate" in request.GET and has_role('SYSA', request.user):
            userid = request.GET["__impersonate"]
            try:
                user = User.objects.get(username__iexact=userid)
            except User.DoesNotExist:
                # create user object if they have never logged in (same thing django_cas does)
                user = User.objects.create_user(userid, '')
                user.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("impersonating %s on page %s") % (userid, request.path), related_object=user)
            l.save()

            request.user = user



    def process_response(self, request, response):
        if isinstance(response, HttpResponseRedirect):
            if  "__impersonate" in request.GET and has_role('SYSA', request.user):
                location = response["Location"]
                if "?" in location:
                    location += "&"
                else:
                    location += "?"
                location += "__impersonate=%s" % request.GET["__impersonate"]
                response["Location"] = location
        return response
