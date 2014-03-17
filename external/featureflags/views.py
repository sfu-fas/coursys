from django.http import HttpResponse

def service_unavailable(request, *args, **kwargs):
    response = HttpResponse()
    response.status_code = 503
    return response
    return HttpError(request, status=503, title="Service Unavailable", error="This feature has been temporarily disabled due to server maintenance or load.", errormsg=None, simple=False)
