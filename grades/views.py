from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering
from courselib.auth import requires_course_by_slug
from grades.models import ACTIVITY_STATUS

@login_required
def index(request):
    # TODO: should distinguish student/TA/instructor roles in template
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("grades/index.html", {'memberships': memberships}, context_instance=RequestContext(request))
    
    
# Todo: Role authentication required
@requires_course_by_slug
def course(request, course_slug):
    """
    Course front page
    """
    course = CourseOffering.objects.get(slug=course_slug)
    activities = course.activity_set.all()
    context = {'course': course, 'activities': activities}
    return render_to_response("grades/course.html", context,
                              context_instance=RequestContext(request))