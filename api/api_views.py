from rest_framework import views
from rest_framework.response import Response
from rest_framework.reverse import reverse

class APIRoot(views.APIView):
    """
    An API endpoint purely for HATEOAS discoverability.
    """
    def get(self, request, format=None):
        data = {'links': {
            'user_offerings': reverse('api.MyOfferings', request=request)
        }}
        return Response(data)
