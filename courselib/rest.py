from oauth_provider.utils import get_oauth_request
from oauth_provider.models import Token
from api.models import ConsumerInfo
from rest_framework import permissions, authentication

class APIPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            # must be authenticated one way or another
            return False

        authenticator = request.successful_authenticator
        required_permissions = view.required_permissions

        if isinstance(authenticator, authentication.SessionAuthentication):
            # CAS authenticated: the world is your oyster
            return True

        else:
            # OAuth authenticated: check that the consumer is allowed to do these things
            assert isinstance(authenticator, authentication.OAuthAuthentication)

            # re-find the Token, since it isn't stashed in the request
            oauth_req = get_oauth_request(request)
            token = Token.objects.get(key=oauth_req['oauth_token'], consumer__key=oauth_req['oauth_consumer_key'])
            allowed_perms = ConsumerInfo.allowed_permissions(token)

            return set(required_permissions) <= set(allowed_perms)
