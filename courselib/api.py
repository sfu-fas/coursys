from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
from oauth_provider.decorators import oauth_required

api_auth_required = oauth_required

# from http://www.django-rest-framework.org/tutorial/1-serialization
class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)