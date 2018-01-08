from oauth_provider.utils import get_oauth_request
from oauth_provider.models import Token
from rest_framework_oauth.authentication import OAuthAuthentication
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

        elif isinstance(authenticator, OAuthAuthentication):
            # OAuth authenticated: check that the consumer is allowed to do these things

            # re-find the Token, since it isn't stashed in the request
            # could be avoided if: http://code.larlet.fr/django-oauth-plus/issue/40/set-requestconsumer-and-requesttoken-to
            oauth_req = get_oauth_request(request)
            token = Token.objects.get(key=oauth_req['oauth_token'], consumer__key=oauth_req['oauth_consumer_key'])

            # consumer must have asked for all of the permissions being used
            allowed_perms = ConsumerInfo.allowed_permissions(token)
            return set(required_permissions) <= set(allowed_perms)

        else:
            raise ValueError("Unknown authentication method.")


class IsOfferingMember(permissions.BasePermission):
    """
    Check that the authenticated user is a (non-dropped) member of the course.
    """
    def has_permission(self, request, view):
        if 'course_slug' not in view.kwargs:
            return False

        if not hasattr(view, 'offering'):
            offering = get_object_or_404(CourseOffering, slug=view.kwargs['course_slug'])
            view.offering = offering

        if not hasattr(view, 'member'):
            assert request.user.is_authenticated()
            member = Member.objects.exclude(role='DROP').filter(offering=offering, person__userid=request.user.username).first()
            view.member = member

        return bool(view.member)

class IsOfferingStaff(permissions.BasePermission):
    """
    Check that the authenticated user is an instructor or TA for the course
    """
    def has_permission(self, request, view):
        if 'course_slug' not in view.kwargs:
            return False

        if not hasattr(view, 'offering'):
            offering = get_object_or_404(CourseOffering, slug=view.kwargs['course_slug'])
            view.offering = offering

        if not hasattr(view, 'member'):
            assert request.user.is_authenticated()
            member = Member.objects.filter(role__in=['INST', 'TA', 'APPR']).filter(offering=offering, person__userid=request.user.username).first()
            view.member = member

        return bool(view.member)

from django.core.cache import caches
from django.utils.encoding import force_bytes, iri_to_uri
from django.utils.cache import patch_response_headers, patch_cache_control
from rest_framework.response import Response
import hashlib
MAX_KEY_LENGTH = 200
class CacheMixin(object):
    """
    View mixin to cache responses based on username (whether they are authenticated by session, oauth, ...).

    Does this by caching the Response object *before* it is rendered into JSON, HTML, etc.  What goes in the cache is
    kwargs to rebuild the rest_framework.response.Response object.

    Assumes that your response data is serializable into your cache, which seems pretty likely.
    """
    cache_hours = 1 # number of hours to cache the response (Expires header and local cache)
    cache_ignore_auth = False # set to True if view can be cached without regard to who is fetching it

    def __init__(self, *args, **kwargs):
        super(CacheMixin, self).__init__(*args, **kwargs)

        # borrowed from FetchFromCacheMiddleware
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = caches[self.cache_alias]

    def _get_cache_key(self, request):
        """
        Generate cache key that's exactly unique enough.

        Assumes that the response is determined by the request.method, authenticated user, and URL path.
        """
        # HTTP method
        method = request.method

        # Authenticated username
        if not request.user.is_authenticated() or self.cache_ignore_auth:
            username = '*'
        else:
            username = request.user.username

        # URL path
        url = force_bytes(iri_to_uri(request.get_full_path()))

        # build a cache key out of that
        key = '#'.join(('CacheMixin', self.key_prefix, username, method, url))
        if len(key) > MAX_KEY_LENGTH:
            # make sure keys don't get too long
            key = key[:(MAX_KEY_LENGTH - 33)] + '-' + hashlib.md5(key).hexdigest()

        return key

    def _timeout(self):
        return self.cache_hours * 3600

    @property
    def default_response_headers(self):
        # shouldn't be necessary since we're setting "cache-control: private" and delivering by HTTPS, but be sure
        # there's no cross-contamination in caches
        h = super(CacheMixin, self).default_response_headers
        h['Vary'] = 'Accept, Authorization, Cookie'
        return h

    def cached_response(self, handler, request, *args, **kwargs):
        # make sure we're actually being asked to do something
        timeout = self._timeout()
        if timeout <= 0:
            return handler(request, *args, **kwargs)

        # check the cache
        cache_key = self._get_cache_key(request)
        response_kwargs = self.cache.get(cache_key)
        if response_kwargs:
            # found it in the cache: hooray!
            return Response(**response_kwargs)

        # actually generate the response
        response = handler(request, *args, **kwargs)

        # ignore errors and streamed responses: borrowed from from UpdateCacheMiddleware
        if response.streaming or response.status_code != 200:
            return response

        response['Cache-control'] = 'private'
        patch_response_headers(response, cache_timeout=timeout)

        # cache the response
        assert isinstance(response, Response), "the response must be a rest_framework.response.Response instance"
        response_kwargs = {
            'data': response.data,
            'status': response.status_code,
            'template_name': response.template_name,
            'headers': dict(list(response._headers.values())),
            'exception': response.exception,
            'content_type': response.content_type,
        }
        self.cache.set(cache_key, response_kwargs, timeout)

        return response

    def get(self, request, *args, **kwargs):
        """
        Return the correct cached GET response.
        """
        if hasattr(self, 'cached_get'):
            handler = self.cached_get
        else:
            handler = super(CacheMixin, self).get
        return self.cached_response(handler, request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        """
        Return the correct cached HEAD response.

        Imitate the logic in django.views.generic.base.View.as_view.view which uses .get() in place of .head() if it's
        not there.
        """
        spr = super(CacheMixin, self)
        if hasattr(self, 'cached_get') and not hasattr(self, 'cached_head'):
            handler = self.cached_get
        elif hasattr(self, 'cached_head'):
            handler = self.cached_head
        elif hasattr(spr, 'get') and not hasattr(spr, 'head'):
            handler = spr.get
        else:
            handler = spr.head
        return self.cached_response(handler, request, *args, **kwargs)


class HyperlinkCollectionField(fields.Field):
    def __init__(self, hyperlink_data, help_text='links to additional information about this object', **kwargs):
        super(HyperlinkCollectionField, self).__init__( read_only=True, help_text=help_text, **kwargs)
        self.hyperlink_data = hyperlink_data
        self.label = None

    def to_representation(self, value):
        result = {}
        for link in self.hyperlink_data:
            label = link['label']
            kwargs = copy.copy(link)
            del kwargs['label']

            field = relations.HyperlinkedRelatedField(read_only=True, **kwargs)
            # fake the request into the context so the URL can be constructed
            field._context = {'request': self.context.get('request', None)}
            result[label] = field.to_representation(value)
        return result

    def get_attribute(self, instance):
        # fake this out to prevent an exception trying to get data we don't care about
        return instance


system_tz = pytz.timezone(settings.TIME_ZONE)

def utc_datetime(dt):
    """
    Convert the local datetime value from the database to UTC, since that's just better for the API.
    """
    if dt:
        return system_tz.normalize(system_tz.localize(dt)).astimezone(pytz.utc)
    else:
        return None
