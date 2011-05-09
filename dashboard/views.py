#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Count
from django.views.decorators.cache import cache_page
from django.conf import settings
from coredata.models import Member, CourseOffering, Person, Role, Semester, MeetingTime
from grades.models import Activity, NumericActivity
from courselib.auth import requires_course_staff_by_slug, requires_course_by_slug, NotFoundResponse
from dashboard.models import NewsItem, UserConfig
from dashboard.forms import *
from django.contrib import messages
from log.models import LogEntry
import random, datetime, time, json

from icalendar import Calendar, Event
import pytz

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
    # if a mobile device request for a non-mobile page
    # check the cookie, continue only when 'no-mobile' is set to 'Yes'
    if request.is_mobile:
        if "no-mobile" in request.COOKIES and request.COOKIES["no-mobile"] == "Yes":
            pass
        else:
            return HttpResponseRedirect(reverse('mobile.views.index'))
        
    userid = request.user.username
    memberships = _get_memberships(userid)
    staff_memberships = [m for m in memberships if m.role in ['INST', 'TA', 'APPR']] # for docs link
    news_list = _get_news_list(userid, 5)
    roles = _get_roles(userid)

    context = {'memberships': memberships, 'staff_memberships': staff_memberships, 'news_list': news_list, 'roles': roles}
    return render_to_response("dashboard/index.html",context,context_instance=RequestContext(request))

def _get_memberships(userid):
    today = datetime.date.today()
    past1 = today.replace(year=today.year-1) # 1 year ago
    past2 = today.replace(year=today.year-2) # 2 years ago
    memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
            .filter(offering__graded=True, person__userid=userid) \
            .filter(offering__semester__end__gte=past2) \
            .annotate(num_activities=Count('offering__activity')) \
            .select_related('offering','offering__semester')
    memberships = [m for m in memberships if _display_membership(m, today, past1)]
    return memberships

def _get_roles(userid):
    return set((r.role for r in Role.objects.filter(person__userid=userid)))

def _get_news_list(userid, count):
    past_1mo = datetime.datetime.today() - datetime.timedelta(days=30) # 1 month ago
    return NewsItem.objects.filter(user__userid=userid, updated__gte=past_1mo).order_by('-updated').select_related('course')[:count]

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
    
    if news_list:
        updated = news_list[0].rfc_updated()
    else:
        # no news items -> no recent updates.
        updated = '2000-01-01T00:00:00Z'

    context = {"news_list": news_list, 'person': user, 'updated': updated, 'server_url': settings.BASE_ABS_URL}
    return render_to_response("dashboard/atom_feed.xml", context, context_instance=RequestContext(request),mimetype="application/atom+xml")


def _weekday_range(start_date, end_date, wkday):
    """
    Return weekly days from start_date to end_date, on given day of week.
    """
    # make sure we've got the right weekday to start with
    date = start_date
    while wkday != date.weekday():
        date += datetime.timedelta(days=1)

    # go through the weeks
    while date <= end_date:
        yield date
        date += datetime.timedelta(7)


#@cache_page(60 * 15)
def calendar_ical(request, token, userid):
    """
    Return an iCalendar for this user, authenticated by the token in the URL
    """
    local_tz = pytz.timezone(settings.TIME_ZONE)
    user = get_object_or_404(Person, userid=userid)
    
    # make sure the token in the URL (32 hex characters) matches the token stored in the DB
    config = _get_calendar_config(user)
    if 'token' not in config or config['token'] != token:
        # no token set or wrong token provided
        return NotFoundResponse(request)
    #else:
        # authenticated

    memberships = Member.objects.filter(person=user, offering__graded=True).exclude(role="DROP")
    classes = set((m.offering for m in memberships))
    class_list = MeetingTime.objects.filter(offering__in=classes)
    
    cal = Calendar()
    cal.add('prodid', '-//SFU Course Management System//courses.cs.sfu.ca//')
    cal.add('version', '2.0')

    for mt in class_list:
        for date in _weekday_range(mt.start_day, mt.end_day, mt.weekday): # for every day the class happens...
            e = Event()
            if mt.exam:
                e.add('summary', '%s exam' % (mt.offering.name()))
            else:
                e.add('summary', '%s lecture' % (mt.offering.name()))
        
            start = local_tz.localize(datetime.datetime.combine(date, mt.start_time))
            e.add('dtstart', start)
            end = local_tz.localize(datetime.datetime.combine(date, mt.end_time))
            e.add('dtend', end)
        
            e.add('location', mt.offering.get_campus_display() + " " + mt.room)
            e['uid'] = mt.offering.slug.replace("-","") + "-" + str(mt.id) + "-" + start.strftime("%Y%m%dT%H%M%S") + '@courses.cs.sfu.ca'

            cal.add_component(e)

    # add every assignment with a due datetime
    
    return HttpResponse(cal.as_string(), mimetype="text/calendar")


def _get_calendar_config(user):
    configs = UserConfig.objects.filter(user=user, key="calendar-config")
    if not configs:
        return {}
    else:
        return json.loads(configs[0].value)


@login_required
def calendar_config(request):
    user = get_object_or_404(Person, userid=request.user.username)
    config = _get_calendar_config(user)
    if 'token' not in config:
        token = None
    else:
        token = config['token']
    
    context={'token': token, 'userid': user.userid, 'server_url': settings.BASE_ABS_URL}
    return render_to_response("dashboard/calendar_config.html", context, context_instance=RequestContext(request))



@login_required
def create_calendar_url(request):
    user = get_object_or_404(Person, userid=request.user.username)
    config = _get_calendar_config(user)
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            token = new_feed_token()
            config['token'] = token
            uc = UserConfig.objects.filter(user=user, key="calendar-config")
            if uc:
                uc = uc[0]
                uc.value = json.dumps(config)
            else:
                uc = UserConfig(user=user, key="calendar-config", value=json.dumps(config))
            uc.save()
            messages.add_message(request, messages.SUCCESS, 'Calendar URL configured.')
            return HttpResponseRedirect(reverse(calendar_config))
    else:
        if 'token' in config:
            # pre-check if we're changing the token
            form = FeedSetupForm({'agree': True})
        else:
            form = FeedSetupForm()

    context = {'form': form}
    return render_to_response("dashboard/calendar_url.html", context, context_instance=RequestContext(request))


@login_required
def disable_calendar_url(request):
    user = get_object_or_404(Person, userid=request.user.username)
    config = _get_calendar_config(user)
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            if 'token' in config:
                del config['token']
                uc = UserConfig.objects.filter(user=user, key="calendar-config")
                if uc:
                    uc = uc[0]
                    uc.value = json.dumps(config)
                    uc.save()

            messages.add_message(request, messages.SUCCESS, 'External calendar disabled.')
            return HttpResponseRedirect(reverse(calendar_config))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render_to_response("dashboard/disable_calendar_url.html", context, context_instance=RequestContext(request))



# Management of feed URL tokens

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
    
    context={'token': token, 'userid': user.userid, 'server_url': settings.BASE_ABS_URL}
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
            configs = UserConfig.objects.filter(user=user, key="feed-token")
            configs.delete()
            messages.add_message(request, messages.SUCCESS, 'External feed disabled.')
            return HttpResponseRedirect(reverse(news_config))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render_to_response("dashboard/disable_news_url.html", context, context_instance=RequestContext(request))



# documentation views

def list_docs(request):
    context = {}
    return render_to_response("docs/index.html", context, context_instance=RequestContext(request))

def view_doc(request, doc_slug):
    context = {'BASE_ABS_URL': settings.BASE_ABS_URL}
    
    # set up useful context variables for this doc
    if doc_slug == "submission":
        instructor = Member.objects.filter(person__userid=request.user.username, offering__graded=True, role__in=["INST","TA"])
        offerings = [m.offering for m in instructor]
        activities = Activity.objects.filter(offering__in=offerings).annotate(Count('submissioncomponent')).order_by('-offering__semester', '-due_date')
        # decorate to prefer (1) submission configured, (2) has due date.
        activities = [(a.submissioncomponent__count==0, not bool(a.due_date), a) for a in activities]
        activities.sort()
        if activities:
            context['activity'] = activities[0][2]
            context['course'] = context['activity'].offering
        elif offerings:
            context['course'] = offerings[0]
        else:
            sem = Semester.objects.all().reverse()[0]
            context['cslug'] = sem.name + '-cmpt-001-d100' # a sample contemporary course slug 

    elif doc_slug == "impersonate":
        instructor = Member.objects.filter(person__userid=request.user.username, offering__graded=True, role__in=["INST","TA"])
        offerings = [(Member.objects.filter(offering=m.offering, role="STUD"), m.offering) for m in instructor]
        offerings = [(students.count()>0, course.semester.name, students, course) for students, course in offerings]
        offerings.sort()
        offerings.reverse()
        if offerings:
            nonempty, semester, students, course = offerings[0]
            context['course'] = course
            if students:
                context['student'] = students[0]
        else:
            sem = Semester.objects.all().reverse()[0]
            context['cslug'] = sem.name + '-cmpt-001-d100' # a sample contemporary course slug 

    elif doc_slug == "calc_numeric":
        instructor = Member.objects.filter(person__userid=request.user.username, offering__graded=True, role__in=["INST","TA"])
        offering_ids = [m.offering.id for m in instructor]
        offerings = CourseOffering.objects.filter(id__in=offering_ids).annotate(Count('activity'))
        # decorate to prefer (1) recent offerings, (2) many activities
        offerings = [(o.semester, o.activity__count, o) for o in offerings if o.activity__count>0]
        offerings.sort()
        if offerings:
            sem, count, course = offerings[0]
            context['course'] = course
            activities = NumericActivity.objects.filter(offering=course, deleted=False)
            context['activities'] = activities
            if activities.count() > 1:
                context['act1'] = activities[0]
                context['act2'] = activities[1]
            elif activities.count() > 0:
                context['act1'] = activities[0]
                context['act2'] = None
            else:
                context['act1'] = None
                context['act2'] = None
           
        else:
            context['course'] = None
            context['act1'] = None
            context['act2'] = None

    return render_to_response("docs/doc_" + doc_slug + ".html", context, context_instance=RequestContext(request))
    
    
