from django.views.decorators.http import require_GET

from coredata.serializers import CourseOfferingSerializer
from dashboard.views import _get_memberships

from courselib.api import JSONResponse

@require_GET
def my_offerings(request):
    userid = 'ggbaker'
    memberships, _ = _get_memberships(userid)
    offerings = [m.offering for m in memberships]
    serializer = CourseOfferingSerializer(offerings, many=True)
    return JSONResponse(serializer.data)
