#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person
from courselib.auth import requires_course_staff_by_slug, requires_course_by_slug, NotFoundResponse
from dashboard.models import NewsItem, UserConfig
from dashboard.forms import *
from contrib import messages
from log.models import LogEntry
import random

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP", offering__component="CAN") \
            .filter(offering__graded=True, person__userid=userid) \
            .select_related('offering','person','offering__semester')
    news_list = NewsItem.objects.filter(user__userid=userid).order_by('-updated').select_related('course')[:5]

    context = {'memberships': memberships ,'news_list': news_list}
    return render_to_response("dashboard/index.html",context ,context_instance=RequestContext(request))


@requires_course_staff_by_slug
def new_message(request, course_slug):
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



def atom_feed(request, token, userid):
    """
    Return an Atom feed for this user, authenticated by the token in the URL
    """
    user = get_object_or_404(Person, userid=userid)
    
    # make sure the token in the URL (32 hex characters) matches the token stored in the DB
    configs = UserConfig.objects.filter(user=user, key="feed-token")
    if not configs or configs[0].value != token:
        # no token configured or wrong token provided
        return NotFoundResponse(request)
    #else:
        # authenticated

    news_list = NewsItem.objects.filter(user=user).order_by('-updated')[:20]
    
    url = _server_base(request)

    context = {"news_list": news_list, 'person': user, 'updated': news_list[0].updated, 'server_url': url}
    return render_to_response("dashboard/atom_feed.xml", context, context_instance=RequestContext(request),mimetype="application/atom+xml")



# Management of feed URL tokens

def _server_base(request):
    "Build base URL for the server for URIs and links"
    if request.is_secure():
        url = "https://"
    else:
        url = "http://"
    url += request.META['SERVER_NAME'] + ":" + request.META['SERVER_PORT']
    return url

@login_required
def news_list(request):
    user = get_object_or_404(Person, userid = request.user.username)
    news_list = NewsItem.objects.filter(user = user).order_by('-updated')
    
    return render_to_response("dashboard/all_news.html", {"news_list": news_list}, context_instance=RequestContext(request))

@login_required
def news_config(request):
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key="feed-token")
    if not configs:
        token = None
    else:
        token = configs[0].value
    
    url = _server_base(request)
    context={'token': token, 'userid': user.userid, 'server_url': url}
    return render_to_response("dashboard/news_config.html", context, context_instance=RequestContext(request))

@login_required
def create_news_url(request):
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key="feed-token")
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            token = new_feed_token()
            if configs:
                c = configs[0]
                c.value = token
            else:
                c = UserConfig(user=user, key="feed-token", value=token)
            c.save()
            messages.add_message(request, messages.SUCCESS, 'Feed URL configured.')
            return HttpResponseRedirect(reverse(news_config))
    else:
        if configs:
            # pre-check if we're changing the token
            form = FeedSetupForm({'agree': True})
        else:
            form = FeedSetupForm()

    context = {'form': form}
    return render_to_response("dashboard/news_url.html", context, context_instance=RequestContext(request))
    
@login_required
def disable_news_url(request):
    user = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            token = new_feed_token()
            configs = UserConfig.objects.filter(user=user, key="feed-token")
            configs.delete()
            messages.add_message(request, messages.SUCCESS, 'External feed disabled.')
            return HttpResponseRedirect(reverse(news_config))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render_to_response("dashboard/disable_news_url.html", context, context_instance=RequestContext(request))
    


#@requires_course_by_slug
#def course(request, course_slug):
#    """
#    Course front page
#    """
#    course = CourseOffering.objects.get(slug=course_slug)
#    return render_to_response("dashboard/course.html", {'course':course}, context_instance=RequestContext(request))

