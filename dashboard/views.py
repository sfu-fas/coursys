#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person
from courselib.auth import requires_course_staff_by_slug, requires_course_by_slug
from dashboard.models import NewsItem, MessageForm
from contrib import messages
from log.models import LogEntry

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    news_list = NewsItem.objects.filter(user__userid=userid).order_by('-updated').select_related('course')[:5]

    context = {'memberships': memberships ,'news_list': news_list}
    return render_to_response("dashboard/index.html",context ,context_instance=RequestContext(request))


@requires_course_staff_by_slug
def new_message(request,course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    staff = get_object_or_404(Person, userid=request.user.username)
    default_message = NewsItem(user=staff, author=staff, course=offering, source_app="dashboard")
    if request.method =='POST':
        form = MessageForm(request.POST, instance=default_message)
        if form.is_valid()==True:
            form.save()
            class_list = Member.objects.exclude(role="DROP").filter(offering=offering).exclude(person=staff)
            for p in class_list:
                stu_message = NewsItem(user = p.person,author=staff, course=offering, source_app="dashboard")
                stu_message.title = form.cleaned_data['title']
                stu_message.content = form.cleaned_data['content']
                stu_message.url = form.cleaned_data['url']
                stu_message.save()
                
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a message for every student in %s") % (offering),
                  related_object=offering)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'News item created.')
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': offering.slug}))
    else:
        form = MessageForm()
    return render_to_response("dashboard/new_message.html", {"form" : form,'course': offering}, context_instance=RequestContext(request))

@login_required
def news_list(request):
    user = get_object_or_404(Person, userid = request.user.username)
    news_list = NewsItem.objects.filter(user = user).order_by('-updated')
    return render_to_response("dashboard/all_news.html", {"news_list" :news_list}, context_instance=RequestContext(request))


#@requires_course_by_slug
#def course(request, course_slug):
#    """
#    Course front page
#    """
#    course = CourseOffering.objects.get(slug=course_slug)
#    return render_to_response("dashboard/course.html", {'course':course}, context_instance=RequestContext(request))

