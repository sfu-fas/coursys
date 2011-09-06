#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Count
from django.views.decorators.cache import cache_page
from django.views.decorators.gzip import gzip_page
from django.conf import settings
from coredata.models import Member, CourseOffering, Person, Role, Semester, MeetingTime
from grades.models import Activity, NumericActivity
from groups.models import Group, GroupMember
from courselib.auth import requires_course_staff_by_slug, requires_course_by_slug, NotFoundResponse, ForbiddenResponse
from dashboard.models import NewsItem, UserConfig
from dashboard.forms import *
from django.contrib import messages
from log.models import LogEntry
import random, datetime, time, json, urlparse

from icalendar import Calendar, Event, Alarm
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


@login_required
def config(request):
    users = Person.objects.filter(userid=request.user.username)
    if users.count() == 1:
        user = users[0]
    else:
        return NotFoundResponse(request, errormsg="Your account is not known to this system.  There is nothing to configure.")

    # calendar config
    config = _get_calendar_config(user)
    if 'token' not in config:
        caltoken = None
    else:
        caltoken = config['token']

    # feed config
    configs = UserConfig.objects.filter(user=user, key="feed-token")
    if not configs:
        newstoken = None
    else:
        newstoken = configs[0].value['token']
    
    # news config
    configs = UserConfig.objects.filter(user=user, key="newsitems")
    if not configs:
        newsconfig = {'email': False}
    else:
        newsconfig = configs[0].value
    
    context={'caltoken': caltoken, 'newstoken': newstoken, 'newsconfig': newsconfig, 'userid': user.userid, 'server_url': settings.BASE_ABS_URL}
    return render_to_response("dashboard/config.html", context, context_instance=RequestContext(request))


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
            NewsItem.for_members(member_kwargs={'offering': offering}, newsitem_kwargs={
                    'author': staff, 'course': offering, 'source_app': 'dashboard',
                    'title': form.cleaned_data['title'], 'content': form.cleaned_data['content'],
                    'url': form.cleaned_data['url']})

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
def atom_feed(request, token, userid, course_slug=None):
    """
    Return an Atom feed for this user, authenticated by the token in the URL
    """
    user = get_object_or_404(Person, userid=userid)
    
    # make sure the token in the URL (32 hex characters) matches the token stored in the DB
    configs = UserConfig.objects.filter(user=user, key="feed-token")
    if not configs or 'token' not in configs[0].value or configs[0].value['token'] != token:
        # no token configured or wrong token provided
        return NotFoundResponse(request)
    #else:
        # authenticated

    news_list = NewsItem.objects.filter(user=user).order_by('-updated')
    course = None
    if course_slug:
        course = get_object_or_404(CourseOffering, slug=course_slug)
        news_list = news_list.filter(course=course)
    news_list = news_list[:20]
    
    if news_list:
        updated = news_list[0].rfc_updated()
    else:
        # no news items -> no recent updates.
        updated = '2000-01-01T00:00:00Z'

    context = {"news_list": news_list, 'person': user, 'updated': updated, 'course': course, 'server_url': settings.BASE_ABS_URL}
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

@cache_page(60*60*6)
def calendar_ical_old(request, token, userid):
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

    first_semester = Semester.first_relevant()
    memberships = Member.objects.filter(person=user, offering__graded=True, offering__semester__gte=first_semester).exclude(role="DROP").exclude(role="APPR")
    # map of offering_id -> this student's lab section (so we only output the right one)
    labsecs = dict(((m.offering_id, m.labtut_section) for m in memberships))
    classes = set((m.offering for m in memberships))
    class_list = MeetingTime.objects.filter(offering__in=classes).select_related('offering')
    
    cal = Calendar()
    cal.add('version', '2.0')
    cal.add('prodid', '-//SFU CourSys//courses.cs.sfu.ca//')

    for mt in class_list:
        # only output whole-course events and this student's lab section.
        if mt.labtut_section not in [None, labsecs[mt.offering_id]]:
            continue

        for date in _weekday_range(mt.start_day, mt.end_day, mt.weekday): # for every day the class happens...
            e = Event()
            summary = mt.offering.name() + " " + mt.get_meeting_type_display()
            e.add('summary', summary)
        
            start = local_tz.localize(datetime.datetime.combine(date, mt.start_time))
            e.add('dtstart', start)
            end = local_tz.localize(datetime.datetime.combine(date, mt.end_time))
            e.add('dtend', end)
        
            e.add('location', mt.offering.get_campus_display() + " " + mt.room)
            e['uid'] = mt.offering.slug.replace("-","") + "-" + str(mt.id) + "-" + start.strftime("%Y%m%dT%H%M%S") + '@courses.cs.sfu.ca'

            cal.add_component(e)

    # add every assignment with a due datetime
    due_length = datetime.timedelta(minutes=1)
    for m in memberships:
        for a in m.offering.activity_set.filter(deleted=False):
            if not a.due_date:
                continue
            
            e = Event()
            e.add('summary', '%s: %s due' % (a.offering.name(), a.name))
            start = local_tz.localize(a.due_date - due_length)
            e.add('dtstart', start)
            end = local_tz.localize(a.due_date)
            e.add('dtend', end)
            e['uid'] = a.offering.slug.replace("-","") + "-" + str(a.id) + "-" + a.slug.replace("-","") + "-" + a.due_date.strftime("%Y%m%dT%H%M%S") + '@courses.cs.sfu.ca'
            
            cal.add_component(e)
    
    return HttpResponse(cal.as_string(), mimetype="text/calendar")


def _meeting_url(mt):
    return mt.offering.url() or reverse('grades.views.course_info', kwargs={'course_slug': mt.offering.slug})
def _activity_url(act):
    return act.url() or reverse('grades.views.activity_info', kwargs={'course_slug': act.offering.slug, 'activity_slug': act.slug})

# wish there was an easy way to do this in CSS, but fullcalendar makes this much easier
def _meeting_colour(mt):
    if mt.meeting_type in ["MIDT", "EXAM"]:
        return "#c05006"
    elif mt.meeting_type == "LAB":
        return "#0606a0"
    else:
        return "#378006"
def _activity_colour(a):
    return "#800606"


def _calendar_event_data(user, start, end, local_tz, dt_string, colour=False,
        due_before=datetime.timedelta(minutes=1), due_after=datetime.timedelta(minutes=0)):
    """
    Data needed to render either calendar AJAX or iCalendar.  Yields series of event dictionaries.
    """
    memberships = Member.objects.filter(person=user, offering__graded=True).exclude(role="DROP").exclude(role="APPR") \
            .filter(offering__semester__start__lte=end, offering__semester__end__gte=start-datetime.timedelta(days=30))
            # start - 30 days to make sure we catch exam/end of semester events

    # map of offering_id -> this student's lab section (so we only output the right one)
    labsecs = dict(((m.offering_id, m.labtut_section) for m in memberships))
    classes = set((m.offering for m in memberships))
    class_list = MeetingTime.objects.filter(offering__in=classes).select_related('offering')
    
    used_ids = set()
    # meeting times
    for mt in class_list:
        # only output whole-course events and this student's lab section.
        if mt.labtut_section not in [None, labsecs[mt.offering_id]]:
            continue

        for date in _weekday_range(mt.start_day, mt.end_day, mt.weekday): # for every day the class happens...
            st = local_tz.localize(datetime.datetime.combine(date, mt.start_time))
            en = local_tz.localize(datetime.datetime.combine(date, mt.end_time))
            if en < start or st > end:
                continue

            ident = mt.offering.slug.replace("-","") + "-" + str(mt.id) + "-" + st.strftime("%Y%m%dT%H%M%S") + "@courses.cs.sfu.ca"
            assert ident not in used_ids
            used_ids.add(ident)
            title = mt.offering.name() + " " + mt.get_meeting_type_display()
            if dt_string:
                st = st.isoformat()
                en = en.isoformat()

            e = {
                'id': ident,
                'title': title,
                'start': st,
                'end': en,
                'location': mt.offering.get_campus_display() + " " + mt.room,
                'allDay': False,
                #'className': "ev-" + mt.meeting_type,
                'url': urlparse.urljoin(settings.BASE_ABS_URL, _meeting_url(mt)),
                'category': mt.meeting_type,
                }
            if colour:
                e['color'] = _meeting_colour(mt)
            yield e
    
    # add every assignment with a due datetime
    for m in memberships:
        for a in m.offering.activity_set.filter(deleted=False):
            if not a.due_date:
                continue
            st = local_tz.localize(a.due_date - due_before)
            en = end = local_tz.localize(a.due_date + due_after)
            if en < start or st > end:
                continue
            
            ident = a.offering.slug.replace("-","") + "-" + str(a.id) + "-" + a.slug.replace("-","") + "-" + a.due_date.strftime("%Y%m%dT%H%M%S") + "@courses.cs.sfu.ca"
            assert ident not in used_ids
            used_ids.add(ident)
            title = '%s: %s due' % (a.offering.name(), a.name)
            if dt_string:
                st = st.isoformat()
                en = en.isoformat()
            
            e = {
                'id': ident,
                'title': title,
                'start': st,
                'end': en,
                'allDay': False,
                #'className': 'ev-due',
                'url': urlparse.urljoin(settings.BASE_ABS_URL, _activity_url(a)),
                'category': 'DUE',
                }
            if colour:
                e['color'] = _activity_colour(a)
            yield e


@cache_page(60*60*6)
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

    now = datetime.datetime.now()
    start = local_tz.localize(now - datetime.timedelta(days=180))
    end = local_tz.localize(now + datetime.timedelta(days=365))
    
    cal = Calendar()
    cal.add('version', '2.0')
    cal.add('prodid', '-//SFU CourSys//courses.cs.sfu.ca//')
    
    for data in _calendar_event_data(user, start, end, local_tz, dt_string=False):
        e = Event()
        e['uid'] = data['id']
        e.add('summary', data['title'])
        e.add('dtstart', data['start'])
        e.add('dtend', data['end'])
        #e.add('categories', data['category'])
        #if 'url' in data:
        #    e.add('url', data['url'])
        if 'location' in data:
            e.add('location', data['location'])
        cal.add_component(e)
    
    return HttpResponse(cal.as_string(), mimetype="text/calendar")


@login_required
def calendar(request):
    """
    Calendar display: all the hard work is JS/AJAX.
    """
    user = get_object_or_404(Person, userid=request.user.username)
    context = {}
    return render_to_response("dashboard/calendar.html", context, context_instance=RequestContext(request))


@login_required
def calendar_data(request):
    """
    AJAX JSON results for the calendar (rendered by dashboard.views.calendar)
    """
    user = get_object_or_404(Person, userid=request.user.username)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start = local_tz.localize(datetime.datetime.fromtimestamp(int(request.GET['start'])))-datetime.timedelta(days=1)
    end = local_tz.localize(datetime.datetime.fromtimestamp(int(request.GET['end'])))+datetime.timedelta(days=1)

    resp = HttpResponse(mimetype="application/json")
    events = list(_calendar_event_data(user, start, end, local_tz, dt_string=True, colour=True,
            due_before=datetime.timedelta(minutes=1), due_after=datetime.timedelta(minutes=30)))
    json.dump(events, resp)
    return resp


def _get_calendar_config(user):
    configs = UserConfig.objects.filter(user=user, key="calendar-config")
    if not configs:
        return {}
    else:
        return configs[0].value


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
                uc.value = config
            else:
                uc = UserConfig(user=user, key="calendar-config", value=config)
            uc.save()
            messages.add_message(request, messages.SUCCESS, 'Calendar URL configured.')
            return HttpResponseRedirect(reverse('dashboard.views.config'))
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
                    uc.value = config
                    uc.save()

            messages.add_message(request, messages.SUCCESS, 'External calendar disabled.')
            return HttpResponseRedirect(reverse('dashboard.views.config'))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render_to_response("dashboard/disable_calendar_url.html", context, context_instance=RequestContext(request))


@login_required
def news_config(request):
    users = Person.objects.filter(userid=request.user.username)
    if users.count() == 1:
        user = users[0]
    else:
        return NotFoundResponse(request, errormsg="Your account is not known to this system.  There is nothing to configure.")

    # get appropriate UserConfig object
    configs = UserConfig.objects.filter(user=user, key='newsitems')
    if configs:
        config = configs[0]
    else:
        config = UserConfig(user=user, key='newsitems', value={})

    if request.method == 'POST':
        form = NewsConfigForm(request.POST)
        if form.is_valid():
            config.value['email'] = form.cleaned_data['want_email']
            config.save()
            messages.add_message(request, messages.SUCCESS, 'News settings updated.')
            return HttpResponseRedirect(reverse('dashboard.views.config'))
    else:
        initial = {'want_email': 'email' not in config.value or config.value['email']}
        form = NewsConfigForm(initial)

    context = {'form': form}
    return render_to_response("dashboard/news_config.html", context, context_instance=RequestContext(request))




# Management of feed URL tokens

@login_required
def news_list(request):
    user = get_object_or_404(Person, userid = request.user.username)
    news_list = NewsItem.objects.filter(user = user).order_by('-updated')
    
    return render_to_response("dashboard/all_news.html", {"news_list": news_list}, context_instance=RequestContext(request))


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
                c.value = {'token':token}
            else:
                c = UserConfig(user=user, key="feed-token", value={'token':token})
            c.save()
            messages.add_message(request, messages.SUCCESS, 'Feed URL configured.')
            return HttpResponseRedirect(reverse('dashboard.views.config'))
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
            return HttpResponseRedirect(reverse('dashboard.views.config'))
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


# data export views
# public data, so no authentication done
@gzip_page
@cache_page(60 * 60 * 6)
def courses_json(request, semester):
    courses = CourseOffering.objects.filter(semester__name=semester).exclude(component="CAN") \
              .select_related('semester')
    resp = HttpResponse(mimetype="application/json")
    resp['Content-Disposition'] = 'inline; filename=' + semester + '.json'
    crs_data = (c.export_dict() for c in courses)
    json.dump({'courses': list(crs_data)}, resp, indent=1)
    return resp

# only accessible from the SVN server
def repo_list_json(request, semester):
    """
    JSON-formatted list of all SVN repositories that should exist for this semester (and permissions).
    """
    if settings.SVN_SERVER_IP != request.META['REMOTE_ADDR']:
        return ForbiddenResponse(request)
    
    sem = get_object_or_404(Semester, name=semester)
    RepoMemberObjects = Member.objects.filter(offering__semester=sem, offering__subject="CMPT", offering__number__gte="200", offering__graded=True).exclude(offering__component="CAN").select_related('person', 'offering')
    
    # build list of instructors/TAs
    members = RepoMemberObjects.filter(role__in=["INST","TA","APPR"])
    instr = {}
    for m in members:
        key = m.offering.slug
        if key not in instr:
            instr[key] = []
        instr[key].append(m.person.userid)
    
    # list of individual repositories
    members = RepoMemberObjects.filter(role="STUD")
    indiv = [{'course':m.offering.slug, 'userid':m.person.userid, 'instr': instr.get(m.offering.slug, [])} for m in members]
    
    # list of group repositories
    gms = GroupMember.objects.filter(activity__offering__semester=sem, confirmed=True, group__courseoffering__subject="CMPT", group__courseoffering__number__gte="200", group__courseoffering__graded=True).exclude(group__courseoffering__component="CAN").select_related('activity', 'activity__offering', 'student', 'student__person', 'group')
    group_memb = {}
    group_crs = {}
    group_label = {}
    for gm in gms:
        key = gm.activity.offering.slug + "_" + gm.group.slug
        if key not in group_memb:
            group_memb[key] = set()
        group_memb[key].add(gm.student.person.userid)
        group_crs[key] = gm.activity.offering.slug
        group_label[key] = gm.group.slug
    
    groups = []
    for g in group_memb:
        members = list(group_memb[g])
        crs = group_crs[g]
        label = group_label[g]
        groups.append({'label':label, 'course':crs, 'members': members, 'instr': instr.get(crs, [])})
    
    resp = HttpResponse(mimetype="application/json")
    json.dump({'indiv': indiv, 'group': groups}, resp, indent=1)
    return resp

