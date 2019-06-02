from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

from oauth_provider.urls import urlpatterns as oauth_patterns

from rest_framework_swagger.views import get_swagger_view
from courselib.urlparts import COURSE_SLUG, ACTIVITY_SLUG
from api.api_views import APIRoot
from coredata.api_views import MyOfferings, OfferingInfo
from grades.api_views import OfferingActivities, OfferingGrades, OfferingStats, OfferingStudents
from submission.api_views import ActivitySubmissions
from marking.api_views import MarkingDetails

endpoint_v1_patterns = [
    url(r'^offerings/$', MyOfferings.as_view(), name='MyOfferings'),
    url(r'^offerings/' + COURSE_SLUG + '$', OfferingInfo.as_view(), name='OfferingInfo'),
    url(r'^offerings/' + COURSE_SLUG + '/activities$', OfferingActivities.as_view(), name='OfferingActivities'),
    url(r'^offerings/' + COURSE_SLUG + '/grades$', OfferingGrades.as_view(), name='OfferingGrades'),
    url(r'^offerings/' + COURSE_SLUG + '/stats', OfferingStats.as_view(), name='OfferingStats'),
    url(r'^offerings/' + COURSE_SLUG + '/students', OfferingStudents.as_view(), name='OfferingStudents'),
    url(r'^offerings/' + COURSE_SLUG + '/submissions/' + ACTIVITY_SLUG, ActivitySubmissions.as_view(),
        name='ActivitySubmissions'),
    #url(r'^offerings/' + COURSE_SLUG + '/marking/' + ACTIVITY_SLUG, MarkingDetails.as_view(),
    #    name='api.MarkingDetails'),

]
endpoint_v1_patterns = format_suffix_patterns(endpoint_v1_patterns)
schema_view = get_swagger_view(title='CourSys API')

api_patterns = [
    url(r'^1$', APIRoot.as_view(), name='APIRoot'),
    url(r'^1/', include(endpoint_v1_patterns)),
    url(r'^oauth/', include(oauth_patterns)),
    url(r'^docs/', schema_view, name='swagger_base'),
]
