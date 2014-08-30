from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
from oauth_provider.decorators import oauth_required
from oauth_provider.utils import get_oauth_request
from oauth_provider.models import Token
from courselib.auth import HttpError
from api.models import ConsumerInfo

api_auth_required = oauth_required

def requires_api_permissions(perms):
    def perm_check(view_func):
        def view(request, *args, **kwargs):
            # re-find the Token, since it isn't stashed in the request
            oauth_req = get_oauth_request(request)
            token = Token.objects.get(key=oauth_req['oauth_token'], consumer__key=oauth_req['oauth_consumer_key'])
            allowed_perms = ConsumerInfo.allowed_permissions(token)

            if set(perms) <= set(allowed_perms):
                # user has authorized this consumer to do all of these things
                return view_func(request, *args, **kwargs)
            else:
                return HttpError(request, status=403, title="Forbidden", error="User has not authorized all of the necessary permissions for this action.", simple=True)

        return view

    def decorator(view_func):
        # decorator inception...
        return oauth_required(perm_check(view_func))

    return decorator

def requires_api_permission(perm):
    return requires_api_permissions([perm])

# from http://www.django-rest-framework.org/tutorial/1-serialization
class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)