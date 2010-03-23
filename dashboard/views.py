#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person
from courselib.auth import requires_course_by_slug
from dashboard.models import NewsItem, MessageForm

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    news_list = NewsItem.objects.filter(user__userid=userid).order_by('-updated')[:5]

    context = {'memberships': memberships ,'news_list': news_list}
    return render_to_response("dashboard/index.html",context ,context_instance=RequestContext(request))


@requires_course_by_slug
def new_message(request,course_slug):
    offering = get_object_or_404(CourseOffering, slug =course_slug)
    staff = get_object_or_404(Person, userid = request.user.username)
    class_list = Member.objects.filter(offering = offering).exclude(person = staff)
    default_message = NewsItem(user = class_list[0].person,author = staff, course = offering, source_app = "dashboard")
    if request.method =='POST':
        form = MessageForm(request.POST, instance = default_message)
        if form.is_valid()==True:
            form.save()
            for p in class_list:
               # new_message = form.save(commit=False)
                #new_message.user = p.person
                #new_message.save()
                stu_message = NewsItem(author = staff, course = offering, source_app = "dashboard")
                stu_message.user = p.person
                stu_message.title = form.cleaned_data['title']
                stu_message.content =form.cleaned_data['content']
                stu_message.url = form.cleaned_data['url']
                stu_message.save()
            return HttpResponseRedirect(reverse('grades.views.course_info',kwargs={'course_slug': course_slug}))
    else:
        form = MessageForm()
    return render_to_response("dashboard/new_message.html", {"form" : form,"course_slug": course_slug}, context_instance=RequestContext(request))

#@requires_course_by_slug
#def course(request, course_slug):
#    """
#    Course front page
#    """
#    course = CourseOffering.objects.get(slug=course_slug)
#    return render_to_response("dashboard/course.html", {'course':course}, context_instance=RequestContext(request))

