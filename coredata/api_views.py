from django.views.decorators.http import require_GET

from coredata.serializers import CourseOfferingSerializer
from dashboard.views import _get_memberships

from courselib.rest import JSONResponse, requires_api_permission

@requires_api_permission('courses')
@require_GET
def my_offerings(request):
    memberships, _ = _get_memberships(request.user.username)
    offerings = [m.offering for m in memberships]
    serializer = CourseOfferingSerializer(offerings, many=True)
    return JSONResponse(serializer.data)
