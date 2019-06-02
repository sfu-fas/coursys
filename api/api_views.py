from rest_framework import views
from rest_framework.response import Response
from rest_framework.reverse import reverse
from courselib.rest import CacheMixin


class APIRoot(CacheMixin, views.APIView):
    """
    An API endpoint purely for HATEOAS-ish discoverability.
    """
    cache_hours = 24
    cache_ignore_auth = True

    def cached_get(self, request, format=None):
        data = {'links': {
            'user_offerings': reverse('api:MyOfferings', request=request)
        }}
        return Response(data)
