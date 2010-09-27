#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Count
from django.views.decorators.cache import cache_page
from coredata.models import Member, CourseOffering, Person
from courselib.auth import requires_course_staff_by_slug, requires_course_by_slug, NotFoundResponse
from dashboard.models import NewsItem, UserConfig
from dashboard.forms import *
from contrib import messages
from log.models import LogEntry
import random, datetime, time

def _display_membership(m, today, student_cutoff):
    """
    Logic to select memberships that should display
    """
    if m.role in ['TA', 'INST', 'APPR']:
        # staff see the whole initial selection
        return True

    # only display if activities have been defined
    active = m.num_activities>0
    # shorter history; no future courses
    date_okay = m.offering.semester.end >= student_cutoff and m.offering.semester.start <= today

    return active and date_okay

@login_required
def index(request):
    userid = request.user.username
    today = datetime.date.today()
    past1 = today.replace(year=today.year-1) # 1 year ago
    past2 = today.replace(year=today.year-2) # 2 years ago

    memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
            .filter(offering__graded=True, person__userid=userid) \
            .filter(offering__semester__end__gte=past2) \
            .annotate(num_activities=Count('offering__activity')) \
            .select_related('offering','offering__semester')
    memberships = [m for m in memberships if _display_membership(m, today, past1)]

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


@cache_page(60 * 15)
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
    if news_list:
        updated = news_list[0].rfc_updated()
    else:
        # no news items -> no recent updates.
        updated = '2000-01-01T00:00:00Z'

    context = {"news_list": news_list, 'person': user, 'updated': updated, 'server_url': url}
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

