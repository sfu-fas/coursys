from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.contrib import messages
from django.utils.safestring import mark_safe
from coredata.models import Member, CourseOffering, Person
from submission.models import Submission, StudentSubmission, GroupSubmission
from grades.models import all_activities_filter, Activity
from discipline.models import *
from discipline.forms import *
from discipline.content import *
from log.models import LogEntry
from courselib.auth import requires_course_staff_by_slug, requires_role, NotFoundResponse

@requires_course_staff_by_slug
def index(request, course_slug):
    """
    List of cases for the course
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    cases = DisciplineCase.objects.filter(student__offering=course)
    groups = DisciplineGroup.objects.filter(offering=course)
    
    context = {'course': course, 'cases': cases, 'groups': groups}
    return render_to_response("discipline/index.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
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
                  description=("created a discipline group in %s") % (course),
                  related_object=group)
            l.save()
            for userid in form.cleaned_data['students']:
                # create case for each student in the group
                student = Member.objects.get(offering=course, person__userid=userid)
                case = DisciplineCase(student=student, group=group, instructor=instructor)
                case.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a discipline case for %s in group %s") % (userid, group.name),
                      related_object=case)
                l.save()
            return HttpResponseRedirect(reverse('discipline.views.showgroup', kwargs={'course_slug': course_slug, 'group_slug': group.slug}))

    else:
        form = DisciplineGroupForm(offering=course)

    form.fields['students'].choices = student_choices
    context = {'course': course, 'form': form}
    return render_to_response("discipline/newgroup.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def new(request, course_slug, group=False):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    student_choices = [
            (m.person.userid,
               "%s (%s, %s)" % (m.person.sortname(), m.person.emplid, m.person.userid))
            for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    
    if request.method == 'POST':
        form = DisciplineCaseForm(offering=course, data=request.POST)
        form.fields['student'].choices = student_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            case = form.save(commit=False)
            case.instructor = instructor
            case.save()
            form.save_m2m()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a discipline case for %s in %s") % (case.student.person.userid, course),
                  related_object=case)
            l.save()
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineCaseForm(offering=course)

    form.fields['student'].choices = student_choices
    context = {'course': course, 'form': form}
    return render_to_response("discipline/new.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def show(request, course_slug, case_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    
    context = {'course': course, 'case': case}
    return render_to_response("discipline/show.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def showgroup(request, course_slug, group_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(DisciplineGroup, slug=group_slug, offering__slug=course_slug)
    
    context = {'course': course, 'group': group}
    return render_to_response("discipline/showgroup.html", context, context_instance=RequestContext(request))

def _edit_case_info(request, course_slug, case_slug, field):
    """
    View function for all of the "edit this aspect of the case" steps.  Uses the STEP_* dictionaries to get relevant strings/classes.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    FormClass = STEP_FORM[field]
    if request.method == 'POST':
        form = FormClass(request.POST, instance=case)
        if form.is_valid():
            c=form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline case %s in %s: changed %s") % (c.slug, c.student.offering, STEP_DESC[field]),
                  related_object=c)
            l.save()
            messages.add_message(request, messages.SUCCESS, "Updated " + STEP_DESC[field] + '.')
            if hasattr(c, 'just_emailed'):
                messages.add_message(request, messages.INFO, "Email sent to student notifying of case.")
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = FormClass(instance=case)
    
    templates = DisciplineTemplate.objects.filter(field__in=form.fields.keys())
    tempaltesJSON = '[' + ",\n".join((t.toJSON() for t in templates)) + ']'
    groupmembersJSON = case.groupmembersJSON()
    
    context = {'course': course, 'case': case, 'form': form,
        'templatesJSON': mark_safe(tempaltesJSON), 'groupmembersJSON': mark_safe(groupmembersJSON)}
    return render_to_response("discipline/edit_"+field+".html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def edit_notes(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "notes")
@requires_course_staff_by_slug
def edit_contacted(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "contacted")
@requires_course_staff_by_slug
def edit_response(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "response")
@requires_course_staff_by_slug
def edit_meeting(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "meeting")
@requires_course_staff_by_slug
def edit_facts(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "facts")
@requires_course_staff_by_slug
def edit_instr_penalty(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "instr_penalty")
@requires_course_staff_by_slug
def edit_letter_review(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "letter_review")

@requires_course_staff_by_slug
def edit_related(request, course_slug, case_slug):
    """
    View function to edit related items: more difficult than the generic function above.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    
    if request.method == 'POST':
        form = CaseRelatedForm(request.POST)
        form.set_choices(course, case)
        if form.is_valid():
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
            all_sub = dict(((sub.id, sub) for sub in StudentSubmission.objects.filter(activity__offering=course)))
            group_sub = dict(((sub.id, sub) for sub in GroupSubmission.objects.filter(activity__offering=course)))
            all_sub.update(group_sub)
            for subid in form.cleaned_data['submissions']:
                subid = int(subid)
                sub = all_sub[subid]
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
                  description=("edit discipline case %s in %s: changed %s") % (case.slug, case.student.offering, STEP_DESC['related']),
                  related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, "Updated " + STEP_DESC['related'] + '.')
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
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
    
    context = {'course': course, 'case': case, 'form': form, 'templatesJSON': '[]'}
    return render_to_response("discipline/edit_related.html", context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def edit_attach(request, course_slug, case_slug):
    pass

@requires_course_staff_by_slug
def show_letter(request, course_slug, case_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    context = {'course': course, 'case': case}
    return render_to_response("discipline/show_letter.html", context, context_instance=RequestContext(request))

@requires_role("SYSA")
def show_templates(request):
    templates = DisciplineTemplate.objects.all()
    context = {'templates': templates}
    return render_to_response("discipline/show_templates.html", context, context_instance=RequestContext(request))

@requires_role("SYSA")
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
            return HttpResponseRedirect(reverse('discipline.views.show_templates'))
    else:
        form = TemplateForm()
    context = {'form': form}
    return render_to_response("discipline/new_template.html", context, context_instance=RequestContext(request))

@requires_role("SYSA")
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
            return HttpResponseRedirect(reverse('discipline.views.show_templates'))
    else:
        form = TemplateForm(instance=template)
    context = {'template': template, 'form': form}
    return render_to_response("discipline/edit_template.html", context, context_instance=RequestContext(request))

@requires_role("SYSA")
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
    return HttpResponseRedirect(reverse('discipline.views.show_templates'))

