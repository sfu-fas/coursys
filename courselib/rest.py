from oauth_provider.utils import get_oauth_request
from oauth_provider.models import Token
from api.models import ConsumerInfo
from rest_framework import permissions, authentication, fields, relations

from django.shortcuts import get_object_or_404
from django.conf import settings
from coredata.models import CourseOffering, Member
import pytz
import copy

class APIConsumerPermissions(permissions.BasePermission):
    """
    Checks that the user's token has been authorized with all of the actions specified in View.consumer_permissions.

    Implies IsAuthenticated permission check since we need to know who the user is before we can check to see what
    they authorized.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            # must be authenticated one way or another
            return False

        authenticator = request.successful_authenticator
        required_permissions = view.consumer_permissions

        if isinstance(authenticator, authentication.SessionAuthentication):
            # CAS authenticated: the world is your oyster
            return True

        elif isinstance(authenticator, authentication.OAuthAuthentication):
            # OAuth authenticated: check that the consumer is allowed to do these things

            # re-find the Token, since it isn't stashed in the request
            oauth_req = get_oauth_request(request)
            token = Token.objects.get(key=oauth_req['oauth_token'], consumer__key=oauth_req['oauth_consumer_key'])

            # consumer must have asked for all of the permissions being used
            allowed_perms = ConsumerInfo.allowed_permissions(token)
            return set(required_permissions) <= set(allowed_perms)

        else:
            raise ValueError, "Unknown authentication method."


class IsOfferingMember(permissions.BasePermission):
    """
    Check that the authenticated user is a (non-dropped) member of the course.
    """
    def has_permission(self, request, view):
        if not hasattr(view, 'offering'):
            offering = get_object_or_404(CourseOffering, slug=view.kwargs['course_slug'])
            view.offering = offering

        if not hasattr(view, 'member'):
            assert request.user.is_authenticated()
            member = Member.objects.exclude(role='DROP').filter(offering=offering, person__userid=request.user.username).first()
            view.member = member

        return bool(view.member)


class HyperlinkCollectionField(fields.Field):
    """
    Field to represent a collection of links to related views. Used for HATEOAS-style self-documenting.

    Constructor arguments are a 'label', and kwargs to a HyperlinkedIdentityField.
    """
    def __init__(self, data):
        super(fields.Field, self).__init__()
        self.data = data
        self.label = None

    def field_to_native(self, obj, field_name):
        result = {}
        for link in self.data:
            label = link['label']
            kwargs = copy.copy(link)
            del kwargs['label']

            field = relations.HyperlinkedIdentityField(**kwargs)
            field.initialize(self.parent, label)
            result[label] = field.field_to_native(obj, label)
        return result


system_tz = pytz.timezone(settings.TIME_ZONE)

def utc_datetime(dt):
    """
    Convert the local datetime value from the database to UTC, since that's just better for the API.
    """
    if dt:
        return system_tz.normalize(system_tz.localize(dt)).astimezone(pytz.utc)
    else:
        return None