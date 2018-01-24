from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.template import RequestContext, defaultfilters
from django.contrib import messages
from django.utils.safestring import mark_safe
from coredata.models import Member, CourseOffering, Person, Role, Unit
from submission.models import Submission, StudentSubmission, GroupSubmission
from grades.models import all_activities_filter, Activity
from discipline.models import *
from discipline.forms import *
from log.models import LogEntry
from courselib.auth import requires_discipline_user, is_discipline_user, requires_role, requires_global_role, NotFoundResponse, ForbiddenResponse
from django.contrib.auth.decorators import login_required
import re

@requires_discipline_user
def index(request, course_slug):
    """
    Instructor's list of cases for the course
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    cases = DisciplineCaseInstr.objects.filter(offering=course)
    cases = [c.subclass() for c in cases]
    groups = DisciplineGroup.objects.filter(offering=course)
    
    context = {'course': course, 'cases': cases, 'groups': groups}
    return render(request, "discipline/index.html", context)

@requires_discipline_user
def newgroup(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    student_choices = [
            (m.person.userid,
               "%s (%s, %s)" % (m.person.sortname(), m.person.emplid, m.person.userid))
            for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    
    if request.method == 'POST':
        form = DisciplineGroupForm(offering=course, data=request.POST)
        form.fields['students'].choices = student_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            group = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a discipline cluster in %s") % (course),
                  related_object=group)
            l.save()
            for userid in form.cleaned_data['students']:
                # create case for each student in the group
                student = Member.objects.get(offering=course, person__userid=userid)
                case = DisciplineCaseInstrStudent(student=student.person, group=group, owner=instructor, offering=course)
                case.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a discipline case for %s in cluster %s") % (userid, group.name),
                      related_object=case)
                l.save()
            return HttpResponseRedirect(reverse('offering:discipline:showgroup', kwargs={'course_slug': course_slug, 'group_slug': group.slug}))

    else:
        form = DisciplineGroupForm(offering=course)

    form.fields['students'].choices = student_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/newgroup.html", context)

@requires_discipline_user
def new(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    student_choices = [
            (m.person.userid,
               "%s (%s, %s)" % (m.person.sortname(), m.person.emplid, m.person.userid))
            for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    group_choices = [('', '\u2014')] + [(g.id, g.name) for g in DisciplineGroup.objects.filter(offering=course)]

    if request.method == 'POST':
        form = DisciplineCaseForm(offering=course, data=request.POST)
        form.fields['student'].choices = student_choices
        form.fields['group'].choices = group_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            case = form.save(commit=False)
            case.owner = instructor
            case.offering = course
            case.save()
            form.save_m2m()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a discipline case for %s in %s") % (case.student.name(), course),
                  related_object=case)
            l.save()
            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineCaseForm(offering=course)

    form.fields['student'].choices = student_choices
    form.fields['group'].choices = group_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/new.html", context)


@requires_discipline_user
def new_nonstudent(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group_choices = [('', '\u2014')] + [(g.id, g.name) for g in DisciplineGroup.objects.filter(offering=course)]
    
    if request.method == 'POST':
        form = DisciplineInstrNonStudentCaseForm(data=request.POST)
        form.fields['group'].choices = group_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            case = form.save(commit=False)
            case.owner = instructor
            case.offering = course
            case.slug = defaultfilters.slugify(case.first_name + " " + case.last_name)
            case.save()
            form.save_m2m()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a non-student discipline case for %s in %s") % (case.student.name(), course),
                  related_object=case)
            l.save()
            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineInstrNonStudentCaseForm()
    
    form.fields['group'].choices = group_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/new_nonstudent.html", context)


@requires_discipline_user
def show(request, course_slug, case_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    roles = request.session['discipline-'+course_slug] # get roles from session
    if case.public_attachments_size() > MAX_ATTACHMENTS:
        messages.add_message(request, messages.WARNING, 'Total size of public attachments must be at most %s because of email limitations. Please make some of the attachments private.' % (MAX_ATTACHMENTS_TEXT))
    
    context = {'course': course, 'case': case, 'roles': roles}
    return render(request, "discipline/show.html", context)

@requires_discipline_user
def showgroup(request, course_slug, group_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(DisciplineGroup, slug=group_slug, offering__slug=course_slug)
    
    context = {'course': course, 'group': group}
    return render(request, "discipline/showgroup.html", context)


also_set_re = re.compile("also-(?P<field>[[a-z_]+)-(?P<caseid>\d+)")
@requires_discipline_user
def edit_case_info(request, course_slug, case_slug, field):
    """
    View function for all of the "edit this aspect of the case" steps.  Uses the STEP_* dictionaries to get relevant strings/classes.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    # permisson checks
    roles = request.session['discipline-'+course_slug]
    if not case.can_edit(field):
        # once instructor finished, don't allow editing those fields
        return ForbiddenResponse(request, "letter has been sent: cannot edit this field")
    elif isinstance(case, DisciplineCaseInstr) and "INSTR" not in roles:
        # only instructor can edit those fields
        return ForbiddenResponse(request, "only the instructor can edit this field")
    elif isinstance(case, DisciplineCaseChair) and "DEPT" not in roles:
        # only discipline admins can edit chair fields
        return ForbiddenResponse(request, "only the Chair (or delegate) can edit this field")

    FormClass = STEP_FORM[field]
    if request.method == 'POST':
        form = FormClass(request.POST, instance=case)
        if form.is_valid():
            c = form.save()
            if field in PRE_LETTER_STEPS:
                # letter hasn't been reviewed if anything changes
                c.letter_review = False
                c.letter_sent = 'WAIT'
                c.penalty_implemented = False
                c.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline case %s in %s: changed %s") % (c.slug, c.offering, STEP_DESC[field]),
                  related_object=c)
            l.save()
            messages.add_message(request, messages.SUCCESS, "Updated " + STEP_DESC[field] + '.')
            
            # set identical value for group members as requested
            also_contact = []
            for postfield in request.POST:
                match = also_set_re.match(postfield)
                if not match or request.POST[postfield] != "on":
                    continue
                
                field = match.group('field')
                caseid = match.group('caseid')
                cases = DisciplineCaseBase.objects.filter(id=caseid)
                if len(cases) != 1 or cases[0].group != case.group:
                    continue
                c0 = cases[0].subclass()
                if not c0.can_edit(field):
                    messages.add_message(request, messages.ERROR,
                        "Case for %s is finished: cannot update %s." % (c0.student.name(), STEP_DESC[field]))
                    continue

                if field=="contacted" and form.cleaned_data[field]=='MAIL':
                    # special case handled below
                    also_contact.append(c0)
                else:
                    setattr(c0, field, form.cleaned_data[field])
                    if field in PRE_LETTER_STEPS:
                        c0.letter_review = False
                    c0.save()
                    messages.add_message(request, messages.SUCCESS,
                        "Also updated %s for %s." % (STEP_DESC[field], c0.student.name()))
                    
            if hasattr(c, 'send_letter_now'):
                # send instructor's letter
                assert case.public_attachments_size() <= MAX_ATTACHMENTS # should be ensured by "review letter" step
                c.send_letter(_currentuser(request))
                messages.add_message(request, messages.INFO, "Letter sent to student summarizing case.")

            if hasattr(c, 'send_contact_mail'):
                # send initial contact email
                c.send_contact_email()
                messages.add_message(request, messages.INFO, "Email sent to student notifying of case.")
                for c0 in also_contact:
                    textkey = 'also-contact_email_text-' + str(c0.id)
                    if textkey in request.POST and request.POST[textkey]=="on":
                        # only send the email if text was updated too
                        c0.contacted = form.cleaned_data['contacted']
                        c0.contact_email_text = form.cleaned_data['contact_email_text']
                        c0.save()
                        messages.add_message(request, messages.SUCCESS,
                            "Also updated %s for %s." % (STEP_DESC['contacted'], c0.student.name()))
                        c0.send_contact_email()
                        messages.add_message(request, messages.INFO, "Also emailed %s." % (c0.student.name()))
                    else:
                        # if not, give an error message.
                        messages.add_message(request, messages.ERROR,
                            mark_safe('Email not sent to %s since their "Contact Email Text" was not updated. You can <a href="%s">edit their contact info</a> if you wish.'
                            % (c0.student.name(),
                                reverse('offering:discipline:edit_case_info',
                                    kwargs={'field': 'contacted', 'course_slug': course_slug, 'case_slug': c0.slug}))))
            
            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = FormClass(instance=case)
    
    templates = DisciplineTemplate.objects.filter(field__in=list(form.fields.keys()))
    tempaltesJSON = json.dumps([t.JSON_data() for t in templates])
    groupmembersJSON = case.groupmembersJSON()
    hasRelAct = len(case.related_activities())>0
    
    context = {'course': course, 'case': case, 'form': form,
        'templatesJSON': mark_safe(tempaltesJSON), 'groupmembersJSON': mark_safe(groupmembersJSON), 'hasRelAct': hasRelAct}
    if field == 'letter_review':
        context['currentuser'] = _currentuser(request)
    return render(request, "discipline/edit_"+field+".html", context)


def _currentuser(request):
    """
    Return Person associated with the current request
    """
    return Person.objects.get(userid=request.user.username)

def _set_related_items(request, case, course, form):
    """
    Do the work of setting related activities
    """
    # delete any old related objects that we might be replacing (but leave others alone)
    for ro in RelatedObject.objects.filter(case=case):
        Class = ro.content_type.model_class()
        if issubclass(Class, Activity) or issubclass(Class, Submission) or issubclass(Class, Member):
            ro.delete()

    # find selected activities
    all_obj = []
    all_acts = dict(((act.id, act) for act in all_activities_filter(course)))
    for actid in form.cleaned_data['activities']:
        actid = int(actid)
        act = all_acts[actid]
        all_obj.append(act)

    # find selected submissions
    indiv_sub = dict(((sub.id, sub) for sub in StudentSubmission.objects.filter(activity__offering=course)))
    for subid in form.cleaned_data['submissions']:
        subid = int(subid)
        if subid in indiv_sub:
            sub = indiv_sub[subid]
            if case.student == sub.member.person:
                # only if submittor match
                all_obj.append(sub)

    group_sub = dict(((sub.id, sub) for sub in GroupSubmission.objects.filter(activity__offering=course)))
    for subid in form.cleaned_data['submissions']:
        subid = int(subid)
        if subid in group_sub:
            sub = group_sub[subid]
            if sub.group.groupmember_set.filter(student__person=case.student):
                # only if in group
                all_obj.append(sub)

    # find selected members
    all_member = dict(((m.id, m)for m in Member.objects.filter(offering=course, role="STUD")))
    for membid in form.cleaned_data['students']:
        membid = int(membid)
        memb = all_member[membid]
        all_obj.append(memb)

    for o in all_obj:
        ro = RelatedObject(case=case, content_object=o)
        ro.save()

    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("edit discipline case %s in %s: changed %s") % (case.slug, case.offering, STEP_DESC['related']),
          related_object=case)
    l.save()

    case.letter_review = False
    case.letter_sent = 'WAIT'
    case.penalty_implemented = False
    case.save()

@requires_discipline_user
def edit_related(request, course_slug, case_slug):
    """
    View function to edit related items: more difficult than the generic function above.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    if not case.can_edit('related'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)
    
    if request.method == 'POST':
        form = CaseRelatedForm(request.POST)
        form.set_choices(course, case)
        if form.is_valid():
            _set_related_items(request, case, course, form)
            messages.add_message(request, messages.SUCCESS, "Updated " + STEP_DESC['related'] + '.')

            for postfield in request.POST:
                match = also_set_re.match(postfield)
                if not match or request.POST[postfield] != "on":
                    continue
                
                field = match.group('field')
                caseid = match.group('caseid')
                cases = DisciplineCaseBase.objects.filter(id=caseid)
                if len(cases) != 1 or cases[0].group != case.group:
                    continue
                c0 = cases[0].subclass()
                if not c0.can_edit('related'):
                    messages.add_message(request, messages.ERROR,
                        "Case for %s is finished: cannot update %s." % (c0.student.name(), STEP_DESC[field]))
                    continue

                _set_related_items(request, c0, course, form)
                if field in PRE_LETTER_STEPS:
                    c0.letter_review = False
                c0.save()
                messages.add_message(request, messages.SUCCESS,
                    "Also updated %s for %s." % (STEP_DESC[field], c0.student.name()))

            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        initial = {'students': [], 'activities': [], 'submissions': []}
        for ro in case.relatedobject_set.all():
            Class = ro.content_type.model_class()
            if issubclass(Class, Activity):
                initial['activities'].append( str(ro.content_object.id) )
            elif issubclass(Class, Submission):
                initial['submissions'].append( str(ro.content_object.id) )
            elif issubclass(Class, Member):
                initial['students'].append( str(ro.content_object.id) )

        form = CaseRelatedForm(initial=initial)
        form.set_choices(course, case)
    
    groupmembersJSON = case.groupmembersJSON()
    
    context = {'course': course, 'case': case, 'form': form,
            'templatesJSON': '[]', 'groupmembersJSON': mark_safe(groupmembersJSON), 'hasRelAct': 'false'}
    return render(request, "discipline/edit_related.html", context)



@login_required
def view_letter(request, course_slug, case_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    
    # allowed users: instructor/discipline admin, or student if they received the letter.
    if is_discipline_user(request, course_slug):
        is_student = False
        messages.add_message(request, messages.INFO,
                "The student should be able to view the letter at this URL as well." )
    elif request.user.username == case.student.userid and case.letter_sent == 'MAIL':
        is_student = True
    else:
        return ForbiddenResponse(request) 
           
    if case.letter_sent != 'MAIL' or not case.letter_text:
        return ForbiddenResponse(request, errormsg="The letter for this case was not sent by this system.")
    
    context = {'course': course, 'case': case, 'is_student': is_student}
    return render(request, "discipline/view_letter.html", context)




# Attachment editing views

@requires_discipline_user
def edit_attach(request, course_slug, case_slug):
    """
    Front page of the file attachments interface
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    attach_pub = CaseAttachment.objects.filter(case=case, public=True)
    attach_pri = CaseAttachment.objects.filter(case=case, public=False)

    if not case.can_edit('attach'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)

    groupmembersJSON = case.groupmembersJSON()
    context = {'course': course, 'case': case, 'attach_pub': attach_pub, 'attach_pri': attach_pri,
            'templatesJSON': '[]', 'groupmembersJSON': mark_safe(groupmembersJSON)}
    return render(request, "discipline/show_attach.html", context)

@requires_discipline_user
def new_file(request, course_slug, case_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    if not case.can_edit('attach'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)

    if request.method == 'POST':
        form = NewAttachFileForm(case, request.POST, request.FILES)
        if form.is_valid():
            f = form.save()
            mediatype = request.FILES['attachment'].content_type
            f.mediatype = mediatype
            f.save()

            case.letter_review = False
            case.letter_sent = 'WAIT'
            case.penalty_implemented = False
            case.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline case %s in %s: add attachment %s") % (case.slug, case.offering, f.name),
                  related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Created file attachment "%s".' % (f.name))
            return HttpResponseRedirect(reverse('offering:discipline:edit_attach', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = NewAttachFileForm(case)

    context = {'course': course, 'case': case, 'form': form}
    return render(request, "discipline/new_file.html", context)

@login_required
def download_file(request, course_slug, case_slug, fileid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    attach = get_object_or_404(CaseAttachment, case__slug=case_slug, case__offering__slug=course_slug, id=fileid)

    # allowed users: instructor/discipline admin, or student if they received the letter.
    if is_discipline_user(request, course_slug):
        is_student = False
    elif attach.public and request.user.username == case.student.userid and case.letter_sent == 'MAIL':
        is_student = True
    else:
        return ForbiddenResponse(request) 

    if is_student and (case.letter_sent != 'MAIL' or not case.letter_text):
        return ForbiddenResponse(request, errormsg="The letter for this case was not sent by this system.")

    attach.attachment.open()
    resp = HttpResponse(attach.attachment, content_type=attach.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + attach.filename() + '"'

    return resp

@requires_discipline_user
def edit_file(request, course_slug, case_slug, fileid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    attach = get_object_or_404(CaseAttachment, case__slug=case_slug, case__offering__slug=course_slug, id=fileid)

    if not case.can_edit('attach'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)

    if request.method == 'POST':
        form = EditAttachFileForm(request.POST, request.FILES, instance=attach)
        if form.is_valid():
            f = form.save()

            case.letter_review = False
            case.letter_sent = 'WAIT'
            case.penalty_implemented = False
            case.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline case %s in %s: edited attachment %s") % (case.slug, case.offering, f.name),
                  related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Updated file attachment "%s".' % (f.name))
            return HttpResponseRedirect(reverse('offering:discipline:edit_attach', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = EditAttachFileForm(instance=attach)

    context = {'course': course, 'case': case, 'attach': attach, 'form': form}
    return render(request, "discipline/edit_file.html", context)




# Discipline chair/admin views

@requires_role("DISC")
def chair_index(request):
    # discipline admin for these departments
    subunit_ids = Unit.sub_unit_ids(request.units)
    has_global_role = 'UNIV' in (u.label for u in request.units)

    instr_cases = DisciplineCaseInstr.objects.filter(offering__owner__id__in=subunit_ids).select_related('owner')
    # can see cases either (1) in your unit, or (2) in subunits if the letter has been sent
    instr_cases = [c for c in instr_cases if (c.owner in request.units) or (c.letter_sent != 'WAIT')]
    instr_cases = [c.subclass() for c in instr_cases]

    context = {'instr_cases': instr_cases, 'has_global_role': has_global_role}
    return render(request, "discipline/chair-index.html", context)
    
@requires_role("DISC")
def chair_create(request, course_slug, case_slug):
    instr_case = get_object_or_404(DisciplineCaseInstr, slug=case_slug, offering__slug=course_slug)
    instr_case = instr_case.subclass()
    if request.method == 'POST':
        chair_case = instr_case.create_chair_case(request.user.username)
        chair_case.save()
        
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
              description=("created chair's case %s in %s") % (chair_case.slug, chair_case.offering),
              related_object=chair_case)
        l.save()
        messages.add_message(request, messages.SUCCESS, "Created Chair's case.")
        return HttpResponseRedirect(reverse('discipline:chair_show', kwargs={'course_slug': course_slug, 'case_slug': chair_case.slug}))
        
    return HttpResponseRedirect(reverse('discipline:chair_index', kwargs={}))

@requires_role("DISC")
def chair_show(request, course_slug, case_slug):
    case = get_object_or_404(DisciplineCaseChair, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    
    context = {'case': case}
    return render(request, "discipline/chair-show.html", context)


@requires_role("DISC")
def chair_show_instr(request, course_slug, case_slug):
    """
    Display instructor's case for Chair
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    roles = ["DEPT"]
    case.ro_display = True
    
    context = {'course': course, 'case': case, 'roles': roles, 'chair': True}
    return render(request, "discipline/show.html", context)


@requires_global_role('DISC')
def permission_admin(request):
    '''
    View to allow University-level dishonesty case admin manage department-level permissions
    '''
    if 'delete' in request.GET:
        r = get_object_or_404(Role, role__in=['DISC', 'DICC'], id=request.GET['delete'])
        # LOG EVENT#
        l = LogEntry(userid=request.user.username,
                     description=("deleted discipline role %s for %s") % (r.role, r.person.name()),
                     related_object=r.person)
        l.save()
        r.delete()

        messages.add_message(request, messages.SUCCESS, 'Deleted role for %s.' % (r.person.name(),))
        return HttpResponseRedirect(reverse('discipline:permission_admin'))

    disc_roles = Role.objects_fresh.filter(role__in=['DISC', 'DICC']).select_related('person', 'unit')
    context = {
        'disc_roles': disc_roles,
    }
    return render(request, "discipline/permission_admin.html", context)


@requires_global_role('DISC')
def permission_admin_add(request):
    if request.method == 'POST':
        form = DisciplineRoleForm(request.POST)
        if form.is_valid():
            r = form.save()
            l = LogEntry(userid=request.user.username,
                  description=("added discipline role %s for %s") % (r.role, r.person.name()),
                  related_object=r)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added role for %s.' % (r.person.name(),))
            return HttpResponseRedirect(reverse('discipline:permission_admin'))
    else:
        form = DisciplineRoleForm()

    context = {'form': form}
    return render(request, "discipline/permission_admin_add.html", context)


# Template editing views for sysadmin interface

@requires_global_role("SYSA")
def show_templates(request):
    templates = DisciplineTemplate.objects.all()
    context = {'templates': templates}
    return render(request, "discipline/show_templates.html", context)

@requires_global_role("SYSA")
def new_template(request):
    if request.method == 'POST':
        form = TemplateForm(request.POST)
        if form.is_valid():
            t = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("create discipline template %i") % (t.id),
                  related_object=t)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Created template "%s".' % (t.label))
            return HttpResponseRedirect(reverse('sysadmin:show_templates'))
    else:
        form = TemplateForm()
    context = {'form': form}
    return render(request, "discipline/new_template.html", context)

@requires_global_role("SYSA")
def edit_template(request, template_id):
    template = get_object_or_404(DisciplineTemplate, id=template_id)
    if request.method == 'POST':
        form = TemplateForm(request.POST, instance=template)
        if form.is_valid():
            t = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline template %i") % (t.id),
                  related_object=t)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Edited template "%s".' % (t.label))
            return HttpResponseRedirect(reverse('sysadmin:show_templates'))
    else:
        form = TemplateForm(instance=template)
    context = {'template': template, 'form': form}
    return render(request, "discipline/edit_template.html", context)

@requires_global_role("SYSA")
def delete_template(request, template_id):
    template = get_object_or_404(DisciplineTemplate, id=template_id)
    if request.method == 'POST':
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
              description=("deleted discipline template %i") % (template.id),
              related_object=template)
        l.save()
        messages.add_message(request, messages.SUCCESS, 'Deleted template "%s".' % (template.label))
        template.delete()
    return HttpResponseRedirect(reverse('sysadmin:show_templates'))

