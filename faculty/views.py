import datetime

from courselib.auth import requires_role, NotFoundResponse
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template.base import Template
from django.template.context import Context
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering
from grad.models import Supervisor
from ra.models import RAAppointment

from faculty.models import CareerEvent, MemoTemplate, Memo, EVENT_TYPES, EVENT_TYPE_CHOICES, EVENT_TAGS
from faculty.forms import CareerEventForm, MemoTemplateForm, MemoForm, AttachmentForm

import itertools


def _get_faculty_or_404(allowed_units, userid_or_emplid):
    """
    Get the Person who has Role[role=~"faculty"] if we're allowed to see it, or raise Http404.
    """
    sub_unit_ids = Unit.sub_unit_ids(allowed_units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid_or_emplid))
    roles = get_list_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, person=person)
    units = set(r.unit for r in roles)
    return person, units


###############################################################################
# Top-level views (management, etc. Not specific to a faculty member)

@requires_role('ADMN')
def index(request):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')
    fac_roles = itertools.groupby(fac_roles, key=lambda r: r.person)
    fac_roles = [(p, ', '.join(r.unit.informal_name() for r in roles)) for p, roles in fac_roles]

    context = {
        'fac_roles': fac_roles,
    }
    return render(request, 'faculty/index.html', context)



###############################################################################
# Display/summary views for a faculty member

@requires_role('ADMN')
def summary(request, userid):
    """
    Summary page for a faculty member.
    """
    person, _ = _get_faculty_or_404(request.units, userid)
    context = {
        'person': person,
    }
    return render(request, 'faculty/summary.html', context)

@requires_role('ADMN')
def events_list(request, userid):
    """
    Display all career events
    """
    person, _ = _get_faculty_or_404(request.units, userid)

    context = {
        'person': person,
    }
    return render(request, 'faculty/career_events_list.html', context)

@requires_role('ADMN')
def otherinfo(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    # TODO: should some or all of these be limited by request.units?

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=person, added_reason='AUTO') \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')


    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=person) \
            .select_related('person', 'project', 'account')

    context = {
        'person': person,
        'instructed': instructed,
        'supervised': supervised,
        'ras': ras,
    }
    return render(request, 'faculty/otherinfo.html', context)


@requires_role('ADMN')
def view_event(request, userid, event_slug):
    """
    Change existing career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)
    memos = Memo.objects.filter(career_event = instance)
    templates = MemoTemplate.objects.filter(unit__in=request.units, event_type=instance.event_type, hidden=False)

    Handler = EVENT_TYPES[instance.event_type](event=instance)

    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'event': instance,
        'memos': memos,
        'templates': templates,
    }
    return render(request, 'faculty/view_event.html', context)


###############################################################################
# Creation and editing of CareerEvents
@requires_role('ADMN')
def event_type_list(request, userid):
    types = [ # TODO: how do we check is_instant now?
        {'slug': key.lower(), 'name': Handler.NAME, 'is_instant': Handler.IS_INSTANT,
         'affects_teaching': 'affects_teaching' in Handler.FLAGS,
         'affects_salary': 'affects_salary' in Handler.FLAGS}
        for key, Handler in EVENT_TYPE_CHOICES]
    person, _ = _get_faculty_or_404(request.units, userid)
    context = {
        'event_types': types,
        'person': person
    }
    return render(request, 'faculty/event_type_list.html', context)


@requires_role('ADMN')
def create_event(request, userid, handler):
    """
    Create new career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    editor = get_object_or_404(Person, userid=request.user.username)
    
    try:
        Handler = EVENT_TYPES[handler.upper()]
    except KeyError:
        return NotFoundResponse(request)

    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'name': Handler.NAME,
        'event_type': Handler.EVENT_TYPE
    }

    # TODO how to pick the unit to use?
    units = sorted(list(member_units))
    handler = Handler.create_for(person=person, unit=None)
    if request.method == "POST":
        form = handler.get_entry_form(editor=editor, units=member_units, data=request.POST)
        if form.is_valid():
            # Event is created in the handler init
            # Event is updated in the load_form method
            handler.load_from(form)
            handler.save(editor)
            
            return HttpResponseRedirect(handler.event.get_absolute_url())
        else:
            context.update({"event_form": form})
    else:
        # Display new blank form
        form = handler.get_entry_form(editor=editor, units=member_units) 
        context.update({"event_form": form})

    return render(request, 'faculty/career_event_form.html', context)


@requires_role('ADMN')
def change_event(request, userid, event_slug):
    """
    Change existing career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    Handler = EVENT_TYPES[instance.event_type]
    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'event': instance,
        'event_type': Handler.EVENT_TYPE
    }
    handler = Handler(instance)
    if request.method == "POST":
        form = handler.get_entry_form(editor=editor, units=member_units, data=request.POST)
        if form.is_valid():
            handler.load_from(form)
            handler.save(editor)
            context.update({"event": handler.event,
                            "event_form": form})

    else:
        # Display form from db instance
        form = handler.get_entry_form(editor=editor, units=member_units)
        context.update({"event_form": form})

    return render(request, 'faculty/career_event_form.html', context)


###############################################################################
# Management of DocumentAttachments and Memos
@requires_role('ADMN')
def new_attachment(request, userid, event_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = AttachmentForm()
    context = {"event": event,
               "person": person,
               "attachment_form": form}

    if request.method == "POST":
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.career_event = event
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(event.get_absolute_url())
        else:
            context.update({"attachment_form": form})
    
    return render(request, 'faculty/document_attachment_form.html', context)


###############################################################################
# Creating and editing Memo Templates

@requires_role('ADMN')
def manage_event_index(request):
    types = [ 
        {'slug': key.lower(), 'name': Handler.NAME, 'is_instant': Handler.IS_INSTANT,
         'affects_teaching': 'affects_teaching' in Handler.FLAGS,
         'affects_salary': 'affects_salary' in Handler.FLAGS}
        for key, Handler in EVENT_TYPE_CHOICES]

    context = {
               'events': types,          
               }
    return render(request, 'faculty/manage_events_index.html', context)

@requires_role('ADMN')
def memo_templates(request, event_type):
    templates = MemoTemplate.objects.filter(unit__in=request.units, event_type=event_type.upper(), hidden=False)

    context = {
               'templates': templates,
               'event_type_slug':event_type,          
               }
    return render(request, 'faculty/memo_templates.html', context)

@requires_role('ADMN')
def new_memo_template(request, event_type):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    if request.method == 'POST':
        form = MemoTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person  
            f.event_type = event_type.upper()         
            f.save()
            messages.success(request, "Created memo template %s for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(memo_templates, kwargs={'event_type':event_type}))
    else:
        form = MemoTemplateForm()
        form.fields['unit'].choices = unit_choices

    lt = sorted(EVENT_TAGS.iteritems())
    context = {
               'form': form,
               'event_type_slug': event_type,
               'EVENT_TAGS': lt
               }
    return render(request, 'faculty/memo_template_form.html', context)

@requires_role('ADMN')
def manage_memo_template(request, event_type, slug):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    memo_template = get_object_or_404(MemoTemplate, slug=slug)
    if request.method == 'POST':
        form = MemoTemplateForm(request.POST, instance=memo_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.event_type = event_type.upper()             
            f.save()
            messages.success(request, "Updated %s template for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(memo_templates, kwargs={'event_type':event_type}))
    else:
        form = MemoTemplateForm(instance=memo_template)
        form.fields['unit'].choices = unit_choices 

    lt = sorted(EVENT_TAGS.iteritems())
    context = {
               'form': form,
               'memo_template': memo_template,
               'event_type_slug':event_type,
               'EVENT_TAGS': lt,
               }
    return render(request, 'faculty/memo_template_form.html', context)

###############################################################################
# Creating and editing Memos

@requires_role('ADMN')
def new_memo(request, userid, event_slug, memo_template_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    template = get_object_or_404(MemoTemplate, slug=memo_template_slug, unit__in=member_units)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)

    from_choices = [('', u'\u2014')] \
                    + [(r.person.id, "%s. %s, %s" %
                            (r.person.get_title(), r.person.letter_name(), r.get_role_display()))
                        for r in Role.objects.filter(unit=instance.unit)]

    ls = instance.memo_info()

    if request.method == 'POST':
        form = MemoForm(request.POST)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.career_event = instance
            f.unit = template.unit
            f.config.update(ls)
            f.template = template;
            f.save()
            messages.success(request, "Created new %s memo for %s." % (form.instance.template.label, form.instance.career_event.title))            
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))
        else:
            messages.success(request, "error!")   
    else:
        form = MemoForm(initial={'subject': template.subject, 'date': datetime.date.today(), 'to_lines': person.letter_name()})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'template' : template,
               'person': person,
               'event': instance,
               }
    return render(request, 'faculty/new_memo.html', context)

@requires_role('ADMN')
def manage_memo(request, userid, event_slug, memo_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    from_choices = [('', u'\u2014')] \
                    + [(r.person.id, "%s. %s, %s" %
                            (r.person.get_title(), r.person.letter_name(), r.get_role_display()))
                        for r in Role.objects.filter(unit=instance.unit)]

    if request.method == 'POST':
        form = MemoForm(request.POST, instance=memo)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.career_event = instance
            f.save()
            messages.success(request, "Updated memo for %s" % (form.instance.career_event.title))            
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))
        else:
            messages.success(request, "error!")   
    else:
        form = MemoForm(instance=memo, initial={'date': datetime.date.today()})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'person': person,
               'event': instance,
               'memo': memo,
               }
    return render(request, 'faculty/manage_memo.html', context)

@requires_role('ADMN')
def get_memo_text(request, userid, event_slug, memo_template_id):
    """ Get the text from memo template """
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    lt = get_object_or_404(MemoTemplate, id=memo_template_id, unit__in=request.units)
    temp = Template(lt.template_text)
    ls = event.memo_info()
    text = temp.render(Context(ls))

    return HttpResponse(text, content_type='text/plain')

@requires_role('ADMN')
def get_memo_pdf(request, userid, event_slug, memo_slug):
    person,  member_units = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s.pdf"' % (memo_slug)

    memo.write_pdf(response) 
    return response

@requires_role('ADMN')
def view_memo(request, userid, event_slug, memo_slug):
    person,  member_units = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    context = {
               'memo': memo,
               'event': instance,
               'person': person,
               }
    return render(request, 'faculty/view_memo.html', context)
