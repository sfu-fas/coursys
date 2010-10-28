# modified from http://stackoverflow.com/questions/2242909/django-user-impersonation-by-admin

from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from courselib.auth import has_role
from log.models import LogEntry

from coredata.models import Member
from urlparts import COURSE_SLUG
import re

course_path_re = re.compile("^/" + COURSE_SLUG + "/")

class ImpersonateMiddleware(object):
    def process_request(self, request):
        if "__impersonate" in request.GET:
            # impersonation requested: check if it's allowed
            userid = request.GET["__impersonate"]
            match = course_path_re.match(request.path)
            if has_role('SYSA', request.user):
                # for sysadmins: yes.
                pass
            elif match:
                # for instructors of a course: yes, but only within that course's "directory".
                course_slug = match.group('course_slug') # course slug from the URL
                memberships = Member.objects.filter(person__userid=request.user.username, offering__slug=course_slug, role="INST")
                if not memberships:
                    # this person is not an instructor for this course: no
                    return
            else:
                # no for anybody else: just ignore the impersonation request.
                return

            # handle the impersonation
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
