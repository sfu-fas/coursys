from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404, HttpResponseForbidden
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.template import TemplateDoesNotExist
from django.views.decorators.gzip import gzip_page
from django.conf import settings
from django.contrib import messages
from coredata.models import Member, CourseOffering, Person, Role, Semester, MeetingTime, Holiday
from grades.models import Activity, NumericActivity
from privacy.models import RELEVANT_ROLES as PRIVACY_ROLES
from courselib.auth import requires_course_staff_by_slug, NotFoundResponse, \
    has_role, requires_global_role
from courselib.auth import get_person
from courselib.branding import product_name
from dashboard.models import NewsItem, UserConfig, Signature, new_feed_token
from dashboard.forms import FeedSetupForm, NewsConfigForm, SignatureForm, PhotoAgreementForm
from grad.models import GradStudent, Supervisor, STATUS_ACTIVE
from discuss.models import DiscussionTopic
from onlineforms.models import FormGroup
from pages.models import Page, ACL_ROLES
from ra.models import RAAppointment, RARequest
from reports.models import AccessRule
from log.models import LogEntry
import datetime, json, urllib.parse
from courselib.auth import requires_role
from icalendar import Calendar, Event
from haystack.query import SearchQuerySet
from haystack.inputs import AutoQuery, Exact, Clean
from xml.etree.ElementTree import ParseError
from ipware import get_client_ip
import pytz
import itertools
import iso8601
from urllib.parse import urlencode
from urllib.error import HTTPError

@login_required
def index(request):
    userid = request.user.username
    memberships, excluded = Member.get_memberships(userid)
    staff_memberships = [m for m in memberships if m.role in ['INST', 'TA', 'APPR']] # for docs link
    is_instructor = len([m for m in memberships if m.role == 'INST']) > 0  # For TUGs link
    news_list = _get_news_list(userid, 5)
    roles = Role.all_roles(userid)
    is_grad = GradStudent.objects.filter(person__userid=userid, current_status__in=STATUS_ACTIVE).exists()
    has_grads = Supervisor.objects.filter(supervisor__userid=userid, supervisor_type='SEN', removed=False).exists()
    form_groups = FormGroup.objects.filter(members__userid=request.user.username).exists()
    has_ras = RAAppointment.objects.filter(hiring_faculty__userid=request.user.username, deleted=False).exists()
    has_ra_requests = RARequest.objects.filter(Q(supervisor__userid=request.user.username) | Q(author__userid=request.user.username), deleted=False).exists()
    has_reports = AccessRule.objects.filter(person__userid=request.user.username).exists()

    # Only CMPT admins should see the one different TA module.  They can now also see the other module as we hope to
    # transition them over.
    cmpt_taadmn = Role.objects_fresh.filter(person__userid=userid, role='TAAD', unit__label='CMPT').exists()

    context = {'memberships': memberships,
               'staff_memberships': staff_memberships,
               'news_list': news_list,
               'roles': roles,
               'is_grad':is_grad,
               'has_grads': has_grads,
               'has_ras': has_ras,
               'has_ra_requests': has_ra_requests,
               'excluded': excluded,
               'form_groups': form_groups,
               'cmpt_taadmn': cmpt_taadmn,
               'is_instructor': is_instructor,
               'has_reports': has_reports}
    return render(request, "dashboard/index.html", context)

@login_required
def index_full(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
            .filter(offering__graded=True, person__userid=userid) \
            .annotate(num_activities=Count('offering__activity')) \
            .select_related('offering','offering__semester')
    memberships = [m for m in memberships if m.role in ['TA', 'INST', 'APPR'] or m.num_activities>0]

    context = {'memberships': memberships}
    return render(request, "dashboard/index_full.html", context)


def fake_login(request, next_page=None):
    """
    Fake login view for devel without access to the fake CAS server
    """
    import socket
    from django.contrib.auth import login
    from django.contrib.auth.models import User

    if not next_page and 'next' in request.GET:
        next_page = request.GET['next']
    if not next_page:
        next_page = '/'

    hostname = socket.gethostname()
    if settings.DEPLOY_MODE == 'production' or hostname.startswith('courses'):
        # make damn sure we're not in production
        raise NotImplementedError
    
    if 'userid' in request.GET:
        username = request.GET['userid']
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username, '')
            user.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        #LOG EVENT#
        l = LogEntry(userid=user.username,
              description=("fake login as %s from %s") % (user.username, get_client_ip(request)),
              related_object=user)
        l.save()
        return HttpResponseRedirect(next_page)

    response = HttpResponse('<h1>Fake Authenticator</h1><p>Who would you like to be today?</p><form action="">Userid: <input type="text" name="userid" /><br/><input type="submit" value="&quot;Authenticate&quot;" /><input type="hidden" name="next" value="%s" /></form>' % (next_page))
    return response

def fake_logout(request):
    """
    Fake logout view for devel without access to the fake CAS server
    """
    import socket
    hostname = socket.gethostname()
    if settings.DEPLOY_MODE == 'production' or hostname.startswith('courses'):
        # make sure we're not in production
        raise NotImplementedError
    
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect('/')


from django_cas_ng.views import LoginView as CasLoginView
class LoginView(CasLoginView):
    def successful_login(self, request, next_page):
        # create a LogEntry when users log in
        user = request.user
        l = LogEntry(userid=user.username,
                     description=("logged in as %s from %s") % (user.username, get_client_ip(request)),
                     related_object=user)
        l.save()
        return super().successful_login(request, next_page)

    def get(self, request):
        # Override to catch exceptions caused by CAS server not responding, which happens and is beyond our control.
        try:
            return super().get(request)
        except IOError as e:
            # Ignore a minimal set of errors we have actually seen result from CAS outages
            if e.errno in [104, 110, 'socket error']:
                pass

            # HTTPError is a subclass of OSError, which IOError is an alias for.
            # Sometimes, the CAS server seems to just return a 500 internal server error.  Let's handle that the
            # same way as the above case.
            elif isinstance(e, HTTPError):
                if e.code == 500:
                    pass
                else:
                    # Any other HTTPError should bubble up and let us know something horrible has happened.
                    raise HTTPError("Got an HTTP Error when authenticating. The error is: {0!s}.".format(e))

            else:
                raise IOError("The errno is %r: %s." % (e.errno, str(e)))

        except ParseError:
            pass

        error = "<h1>Forbidden</h1><p>Login failed because of a CAS error.</p>"
        return HttpResponseForbidden(error)


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
    # By default, users get emails for news items unless they specifically opted-out.  The value here doesn't
    # change any data, it just displays the same thing as if someone had a UserConfig where they specifically set
    # email to True.
    if not configs:
        newsconfig = {'email': True}
    else:
        newsconfig = configs[0].value
    
    # advisor note API config
    advisor = False
    if has_role('ADVS', request) or has_role('ADVM', request):
        advisor = True
        configs = UserConfig.objects.filter(user=user, key='advisor-token')

    # ID photo agreement
    instructor = False
    if Member.objects.filter(person=user, role__in=['INST', 'TA']).count() > 0:
        instructor = True
        configs = UserConfig.objects.filter(user=user, key='photo-agreement')

    # privacy config
    roles = Role.all_roles(user.userid)
    roles_with_privacy = [r for r in roles if r in PRIVACY_ROLES]
    privacy_visible = len(roles_with_privacy) > 0

    # DA Privacy config
    roles_with_da_privacy = [r for r in roles if r == 'ADMN']
    da_privacy_visible = len(roles_with_da_privacy) > 0

    context={'caltoken': caltoken, 'newstoken': newstoken, 'newsconfig': newsconfig, 'advisor': advisor,
             'instructor': instructor, 'userid': user.userid, 'server_url': settings.BASE_ABS_URL,
             'privacy_visible': privacy_visible, 'da_privacy_visible': da_privacy_visible}
    return render(request, "dashboard/config.html", context)


def _get_news_list(userid, count):
    past_1mo = datetime.datetime.today() - datetime.timedelta(days=20)
    return NewsItem.objects.filter(user__userid=userid, updated__gte=past_1mo).order_by('-updated').select_related('course')[:count]


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
    return render(request, "dashboard/atom_feed.xml", context, content_type="application/atom+xml")



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


def _meeting_url(mt):
    return mt.offering.url() or reverse('offering:course_info', kwargs={'course_slug': mt.offering.slug})
def _activity_url(act):
    return act.url() or reverse('offering:activity_info', kwargs={'course_slug': act.offering.slug, 'activity_slug': act.slug})

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
def _holiday_colour(h):
    return "#060680"

ICAL_SEQUENCE = '3' # used to perturb the icalendar idents when the output changes
def _offerings_calendar_data(offerings, labsecs, start, end, local_tz, dt_string=True, colour=False, browse_titles=False):
    """
    Get calendar data for this set of offerings and lab sections.
    
    Used both in _calendar_event_data and by the course browser (coredata.views.browse_courses_info)
    """

    # holidays and cancellations
    cancellations = set() # days when classes cancelled
    for h in Holiday.objects.filter(date__gte=start, date__lte=end):
        if h.holiday_type in ['FULL', 'CLAS']:
            cancellations.add(h.date)

        ident = "holiday-" + str(h.id) + "-" + h.date.strftime("%Y%m%d") + "-" + ICAL_SEQUENCE + "@courses.cs.sfu.ca"
        title = "%s (%s)" % (h.description, h.get_holiday_type_display())
        dt = h.date
        if dt_string:
            dt = dt.isoformat()
        
        e = {
            'id': ident,
            'title': title,
            'start': dt,
            'end': dt,
            'allDay': True,
            'category': 'HOLIDAY',
            }
        
        if colour:
            e['color'] = _holiday_colour(h)
        yield e

    # map of offering_id -> this student's lab section (so we only output the right one)
    class_list = MeetingTime.objects.filter(offering__in=offerings).select_related('offering')
    
    # meeting times
    for mt in class_list:
        # only output whole-course events and this student's lab section.
        if labsecs and mt.labtut_section not in [None, labsecs[mt.offering_id]]:
            continue

        for date in _weekday_range(mt.start_day, mt.end_day, mt.weekday): # for every day the class happens...
            st = local_tz.localize(datetime.datetime.combine(date, mt.start_time))
            en = local_tz.localize(datetime.datetime.combine(date, mt.end_time))
            if en < start or st > end:
                continue
            if st.date() in cancellations:
                continue
            
            ident = mt.offering.slug.replace("-","") + "-" + str(mt.id) + "-" + st.strftime("%Y%m%dT%H%M%S") + "-" + ICAL_SEQUENCE + "@courses.cs.sfu.ca"
            if browse_titles:
                title = mt.get_meeting_type_display()
                if mt.labtut_section:
                    title += ' ' + mt.labtut_section
            else:
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
                'url': urllib.parse.urljoin(settings.BASE_ABS_URL, _meeting_url(mt)),
                'category': mt.meeting_type,
                }
            if colour:
                e['color'] = _meeting_colour(mt)
            yield e



def _calendar_event_data(user, start, end, local_tz, dt_string, colour=False,
        due_before=datetime.timedelta(minutes=1), due_after=datetime.timedelta(minutes=0)):
    """
    Data needed to render either calendar AJAX or iCalendar.  Yields series of event dictionaries.
    """
    memberships = Member.objects.filter(person=user, offering__graded=True).exclude(role="DROP").exclude(role="APPR")\
        .exclude(offering__component="CAN").filter(offering__semester__start__lte=end,
                                                   offering__semester__end__gte=start-datetime.timedelta(days=30))
            # start - 30 days to make sure we catch exam/end of semester events
    classes = set((m.offering for m in memberships))
    labsecs = dict(((m.offering_id, m.labtut_section) for m in memberships))

    # get all events from _offerings_calendar_data
    for res in _offerings_calendar_data(classes, labsecs, start, end, local_tz, dt_string, colour):
        yield res

    # add every assignment with a due datetime
    for m in memberships:
        for a in m.offering.activity_set.filter(deleted=False):
            if not a.due_date:
                continue
            st = local_tz.localize(a.due_date - due_before)
            en = end = local_tz.localize(a.due_date + due_after)
            if en < start or st > end:
                continue
            
            ident = a.offering.slug.replace("-","") + "-" + str(a.id) + "-" + a.slug.replace("-","") + "-" + a.due_date.strftime("%Y%m%dT%H%M%S") + "-" + ICAL_SEQUENCE + "@courses.cs.sfu.ca"
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
                'url': urllib.parse.urljoin(settings.BASE_ABS_URL, _activity_url(a)),
                'category': 'DUE',
                }
            if colour:
                e['color'] = _activity_colour(a)
            yield e
    

def _ical_datetime(utc, dt):
    if isinstance(dt, datetime.datetime):
        return utc.normalize(dt.astimezone(utc))
    else:
        return dt


def calendar_ical(request, token, userid):
    """
    Return an iCalendar for this user, authenticated by the token in the URL
    """
    local_tz = pytz.timezone(settings.TIME_ZONE)
    utc = pytz.utc
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
    cal.add('X-PUBLISHED-TTL', 'PT1D')
    
    for data in _calendar_event_data(user, start, end, local_tz, dt_string=False):
        e = Event()
        e['uid'] = str(data['id'])
        e.add('summary', data['title'])
        e.add('dtstart', _ical_datetime(utc, data['start']))
        e.add('dtend', _ical_datetime(utc, data['end']))
        if data['category'] in ('DUE', 'HOLIDAY'):
            # these shouldn't be "busy" on calendars
            e.add('transp', 'TRANSPARENT')
        else:
            e.add('transp', 'OPAQUE')

        # spec says no TZID on UTC times
        if 'TZID' in e['dtstart'].params:
            del e['dtstart'].params['TZID']
        if 'TZID' in e['dtend'].params:
            del e['dtend'].params['TZID']
        
        e.add('categories', data['category'])
        if 'url' in data:
            e.add('url', data['url'])
        if 'location' in data:
            e.add('location', data['location'])
        cal.add_component(e)

    resp = HttpResponse(cal.to_ical(), content_type="text/calendar")
    return resp


@login_required
def calendar(request):
    """
    Calendar display: all the hard work is JS/AJAX.
    """
    #user = get_object_or_404(Person, userid=request.user.username)
    context = {}
    return render(request, "dashboard/calendar.html", context)


@login_required
def calendar_data(request):
    """
    AJAX JSON results for the calendar (rendered by dashboard.views.calendar)
    """
    try:
        st = iso8601.parse_date(request.GET['start'])
        en = iso8601.parse_date(request.GET['end'])
    except (KeyError, ValueError, iso8601.ParseError):
        return NotFoundResponse(request, errormsg="Bad request")

    user = get_object_or_404(Person, userid=request.user.username)
    local_tz = pytz.timezone(settings.TIME_ZONE)
    start = st - datetime.timedelta(days=1)
    end = en + datetime.timedelta(days=1)

    resp = HttpResponse(content_type="application/json")
    events = _calendar_event_data(user, start, end, local_tz, dt_string=True, colour=True,
            due_before=datetime.timedelta(minutes=1), due_after=datetime.timedelta(minutes=30))
    json.dump(list(events), resp, indent=1)
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
            return HttpResponseRedirect(reverse('config:config'))
    else:
        if 'token' in config:
            # pre-check if we're changing the token
            form = FeedSetupForm({'agree': True})
        else:
            form = FeedSetupForm()

    context = {'form': form}
    return render(request, "dashboard/calendar_url.html", context)


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
            return HttpResponseRedirect(reverse('config:config'))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render(request, "dashboard/disable_calendar_url.html", context)


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
            return HttpResponseRedirect(reverse('config:config'))
    else:
        initial = {'want_email': 'email' not in config.value or config.value['email']}
        form = NewsConfigForm(initial)

    context = {'form': form}
    return render(request, "dashboard/news_config.html", context)




# Management of feed URL tokens

@login_required
def news_list(request):
    user = get_object_or_404(Person, userid = request.user.username)
    news_list = NewsItem.objects.filter(user = user).order_by('-updated')
    
    return render(request, "dashboard/all_news.html", {"news_list": news_list})


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
            return HttpResponseRedirect(reverse('config:config'))
    else:
        if configs:
            # pre-check if we're changing the token
            form = FeedSetupForm({'agree': True})
        else:
            form = FeedSetupForm()

    context = {'form': form}
    return render(request, "dashboard/news_url.html", context)
    
@login_required
def disable_news_url(request):
    user = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            configs = UserConfig.objects.filter(user=user, key="feed-token")
            configs.delete()
            messages.add_message(request, messages.SUCCESS, 'External feed disabled.')
            return HttpResponseRedirect(reverse('config:config'))
    else:
        form = FeedSetupForm({'agree': True})

    context = {'form': form}
    return render(request, "dashboard/disable_news_url.html", context)


# management of Signature objects by manager

@requires_role('ADMN')
def signatures(request):
    roles = Role.objects_fresh.filter(unit__in=request.units).select_related('person')
    people = [p.person for p in roles]
    sigs = Signature.objects.filter(user__in=people)
    context = {'sigs': sigs}
    return render(request, "dashboard/signatures.html", context)


@requires_role('ADMN')
def view_signature(request, userid):
    roles = Role.objects_fresh.filter(unit__in=request.units).select_related('person')
    people = [p.person for p in roles]
    sig = get_object_or_404(Signature, user__in=people, user__userid=userid)
    
    response = HttpResponse(sig.sig, content_type='image/png')
    response['Content-Disposition'] = 'inline; filename="%s.png"' % (userid)
    response['Content-Length'] = sig.sig.size
    return response

@requires_role('ADMN')
def delete_signature(request, userid):
    roles = Role.objects_fresh.filter(unit__in=request.units).select_related('person')
    people = [p.person for p in roles]
    sig = get_object_or_404(Signature, user__in=people, user__userid=userid)
    
    if request.method == 'POST':
        sig.sig.delete(save=False)
        sig.delete()
        messages.add_message(request, messages.SUCCESS, 'Deleted signature for %s.' % (sig.user.name()))

    return HttpResponseRedirect(reverse('admin:signatures'))

@requires_role('ADMN')
def new_signature(request):
    roles = Role.objects_fresh.filter(unit__in=request.units).select_related('person')
    people = set((p.person for p in roles))
    people = sorted(list(people))
    person_choices = [(p.id, p.sortname()) for p in people]
    
    if request.method == 'POST':
        form = SignatureForm(request.POST, request.FILES)
        form.fields['person'].choices = person_choices
        if form.is_valid():
            person = Person.objects.get(id=form.cleaned_data['person'])
            sig, created = Signature.objects.get_or_create(user=person)
            if not created:
                sig.sig.delete(save=False)
            sig.sig = form.cleaned_data['signature']
            sig.save()
            
            messages.add_message(request, messages.SUCCESS, 'Created signature for %s.' % (sig.user.name()))
            return HttpResponseRedirect(reverse('admin:signatures'))
    else:
        form = SignatureForm()
        form.fields['person'].choices = person_choices
    context = {'form': form}
    return render(request, "dashboard/new_signature.html", context)



def student_info(request, userid=None):
    # old student search view: new search is better in every way.
    messages.add_message(request, messages.INFO, 'The old student search has been replaced with an awesome site search, accessible from the search box at the top of every page in %s.' % (product_name(request),))
    return HttpResponsePermanentRedirect(reverse('dashboard:site_search'))


# documentation views

def list_docs(request):
    context = {}
    return render(request, "docs/index.html", context)


def view_doc(request, doc_slug):
    context = {'BASE_ABS_URL': settings.BASE_ABS_URL}
    
    # set up useful context variables for this doc
    if doc_slug in ["submission", "pages-api"]:
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
            sem = Semester.current()
            context['cslug'] = sem.slugform() + '-cmpt-001-d1' # a sample contemporary course slug 
        
        context['userid'] = request.user.username or 'userid'

    elif doc_slug == "impersonate":
        instructor = Member.objects.filter(person__userid=request.user.username, offering__graded=True, role__in=["INST","TA"])
        offerings = [(Member.objects.filter(offering=m.offering, role="STUD"), m.offering) for m in instructor]
        offerings = [(students.count()>0, course.semester.name, students, course) for students, course in offerings]
        offerings.sort(key=lambda x: (x[0], x[1], x[3]))
        offerings.reverse()
        if offerings:
            nonempty, semester, students, course = offerings[0]
            context['course'] = course
            if students:
                context['student'] = students[0]
        else:
            sem = Semester.current()
            context['cslug'] = sem.slugform() + '-cmpt-001-d1' # a sample contemporary course slug 

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

    elif doc_slug == "search":
        context['two_years'] = datetime.date.today().year - 2

    try:
        res = render(request, "docs/doc_" + doc_slug + ".html", context)
    except TemplateDoesNotExist:
        raise Http404
    return res


# data export views
# public data, so no authentication done
@gzip_page
def courses_json(request, semester):
    offerings = CourseOffering.objects.filter(semester__name=semester)\
        .exclude(component="CAN").exclude(flags=CourseOffering.flags.combined) \
        .select_related('semester').prefetch_related('meetingtime_set')
    instructors = Member.objects.filter(role='INST', offering__semester__name=semester).select_related('person')
    instr_by_offeringid = dict(
        (oid, list(instr))
        for oid, instr
        in itertools.groupby(instructors, lambda m: m.offering_id)
    )

    resp = HttpResponse(content_type="application/json")
    resp['Content-Disposition'] = 'inline; filename="' + semester + '.json"'
    crs_data = (o.export_dict(instructors=instr_by_offeringid.get(o.id, [])) for o in offerings)
    json.dump({'courses': list(crs_data)}, resp, indent=1)
    return resp

@requires_role('ADVS')
def enable_advisor_token(request):
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key="advisor-token")
    if not len(configs) is 0:
        raise Http404
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            config = {'token': new_feed_token()}
            uc = UserConfig(user=user, key="advisor-token", value=config)
            uc.save()
            messages.add_message(request, messages.SUCCESS, 'Advisor notes API enabled')
            return HttpResponseRedirect(reverse('config:config'))
    else:
        form = FeedSetupForm()
    return render(request, "dashboard/enable_advisor_token.html", {"form": form})

@requires_role('ADVS')
def disable_advisor_token(request):
    user = get_object_or_404(Person, userid=request.user.username)
    config = get_object_or_404(UserConfig, user=user, key='advisor-token')
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            config.delete()
            messages.add_message(request, messages.SUCCESS, 'Advisor notes API disabled')
            return HttpResponseRedirect(reverse('config:config'))
    else:
        form = FeedSetupForm({'agree': True})
        
    return render(request, "dashboard/disable_advisor_token.html", {'form': form})

@requires_role('ADVS')
def change_advisor_token(request):
    user = get_object_or_404(Person, userid=request.user.username)
    config = get_object_or_404(UserConfig, user=user, key='advisor-token')
    if request.method == 'POST':
        form = FeedSetupForm(request.POST)
        if form.is_valid():
            config.value['token'] = new_feed_token()
            config.save()
            messages.add_message(request, messages.SUCCESS, 'Advisor notes API token changed')
            return HttpResponseRedirect(reverse('config:config'))
    else:
        form = FeedSetupForm({'agree': True})
        
    return render(request, "dashboard/change_advisor_token.html", {"form": form})

@login_required
def photo_agreement(request):
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key='photo-agreement')
    if configs:
        config = configs[0]
    else:
        config = UserConfig(user=user, key='photo-agreement', value={'agree': False})

    if request.method == 'POST':
        form = PhotoAgreementForm(request.POST)
        if form.is_valid():
            config.value['agree'] = form.cleaned_data['agree']
            if config.value['agree']:
                config.value['version'] = 1
                config.value['at'] = datetime.datetime.now().isoformat()
                config.value['from'] = get_client_ip(request)
            config.save()
            messages.add_message(request, messages.SUCCESS, 'Updated your photo agreement status.')
            if 'return' in request.GET:
                url = request.GET['return']
            else:
                url = reverse('config:config')
            return HttpResponseRedirect(url)
    else:
        form = PhotoAgreementForm({'agree': config.value['agree']})

    if 'at' in config.value:
        agree_date = datetime.datetime.strptime(config.value['at'], '%Y-%m-%dT%H:%M:%S.%f')
    else:
        agree_date = None

    context = {"form": form, 'agree': config.value['agree'], 'agree_date': agree_date}
    return render(request, "dashboard/photo_agreement.html", context)



SEARCH_URL = 'http://www.sfu.ca/search.html?'
MAX_RESULTS = 50
RESULT_TYPE_DISPLAY = { # human-friendly map for result.content_type
    'coredata.courseoffering': 'Course offering',
    'coredata.member': 'Student in your class',
    #'coredata.member': 'TA in your class', # handled in template where we know which role
    'pages.page': 'Class web page',
    'discuss.discussiontopic': 'Discussion topic',
}

def _query_results(query, person):
    """
    Actually build the query results for this person.

    Make sure any result.content_type values are reflected in RESULT_TYPE_DISPLAY for display to the user.
    """
    if len(query) < 2:
        return []

    query = query.replace('@sfu.ca', '') # hack to make email addresses searchable as userids
    query = Clean(query)

    # offerings person was a member of (coredata.CourseOffering)
    if person:
        members = Member.objects.filter(person=person).exclude(role='DROP').select_related('offering')
        offering_slugs = set(m.offering.slug for m in members)
        offering_results = SearchQuerySet().models(CourseOffering).filter(text__fuzzy=query) # offerings that match the query
        offering_results = offering_results.filter(slug__in=offering_slugs) # ... and this person was in
    else:
        members = []
        offering_results = []

    # pages this person can view (pages.Page)
    page_acl = set(['ALL'])
    for m in members:
        # builds a set of offering_slug+"_"+acl_value strings, which will match the permission_key field in the index
        member_acl = set("%s_%s" % (m.offering.slug, acl) for acl in ACL_ROLES[m.role] if acl != 'ALL')
        page_acl |= member_acl

    page_results = SearchQuerySet().models(Page).filter(text__fuzzy=query) # pages that match the query
    page_results = page_results.filter(permission_key__in=page_acl) # ... and are visible to this user

    # discussion this person can view (discussion.DiscussionTopic)
    if person:
        discuss_results = SearchQuerySet().models(DiscussionTopic).filter(text__fuzzy=query) # discussions that match the query
        discuss_results = discuss_results.filter(slug__in=offering_slugs) # ... and this person was in
    else:
        discuss_results = []

    # students taught by instructor (coredata.Member)
    instr_members = Member.objects.filter(person=person, role__in=['INST','TA']).exclude(offering__component='CAN') \
        .select_related('offering')
    if person and instr_members:
        offering_slugs = set(m.offering.slug for m in instr_members)
        member_results = SearchQuerySet().models(Member).filter(text__fuzzy=query) # members that match the query
        member_results = member_results.filter(offering_slug__in=offering_slugs) # ... and this person was the instructor for
        member_results = member_results.load_all()
    else:
        member_results = []

    # combine and limit to best results
    results = itertools.chain(
        offering_results[:MAX_RESULTS],
        page_results[:MAX_RESULTS],
        member_results[:MAX_RESULTS],
        discuss_results[:MAX_RESULTS],
        )
    results = (r for r in results if r is not None)
    results = list(results)
    results.sort(key=lambda result: -result.score)
    results = results[:MAX_RESULTS] # (list before this could be n*MAX_RESULTS long)

    return results

def site_search(request):
    # Things that would be nice:
    # activities in your courses
    # grad students you admin/supervise
    # advisors: students/advisornote content
    # marking comments
    person = get_person(request.user)

    query = request.GET.get('q', '')
    if 'search-scope' in request.GET and request.GET['search-scope'] == 'sfu':
        # redirect to SFU-wide search if appropriate
        url = SEARCH_URL + urlencode({'q': query, 'search-scope': 'sfu'})
        return HttpResponseRedirect(url)

    results = _query_results(query, person)
    if results:
        maxscore = max(r.score for r in results)
    else:
        maxscore = 1
    # strip out the really bad results: elasticsearch is pretty liberal
    results = (r for r in results if r.score >= maxscore/10)

    if request.user.is_authenticated:
        # record authenticated searches for A/B testing
        l = LogEntry(userid=request.user.username,
                 description='User %i searched for %r' % (request.user.id, query),
                 related_object=request.user)
        l.save()

    context = {
        "query": query,
        "results": results,
        "maxscore": maxscore,
    }

    return render(request, "dashboard/site_search.html", context)


@requires_global_role('SYSA')
def frontend_check(request):
    context = {}
    return render(request, "dashboard/frontend_check.html", context)