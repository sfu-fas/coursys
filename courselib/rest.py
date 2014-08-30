from oauth_provider.utils import get_oauth_request
from oauth_provider.models import Token
from api.models import ConsumerInfo
from rest_framework import permissions, authentication

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
