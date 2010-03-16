#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering
from courselib.auth import requires_course_by_slug
from dashboard.models import NewsItem

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    news_list = NewsItem.objects.filter(user__userid=userid).order_by('-updated')[:5]

    context = {'memberships': memberships ,'news_list': news_list}
    return render_to_response("dashboard/index.html",context ,context_instance=RequestContext(request))

#@requires_course_by_slug
#def course(request, course_slug):
#    """
#    Course front page
#    """
#    course = CourseOffering.objects.get(slug=course_slug)
#    return render_to_response("dashboard/course.html", {'course':course}, context_instance=RequestContext(request))

