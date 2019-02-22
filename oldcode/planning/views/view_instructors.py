from planning.models import SemesterPlan, PlannedOffering, TeachingIntention, TeachingCapability
from .update_plan import update_plan
from courselib.auth import requires_role
from coredata.models import Person
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def view_instructors(request, semester, plan_slug, planned_offering_slug):
    semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
    planned_offering = get_object_or_404(PlannedOffering, slug=planned_offering_slug)

    all_instructors = Person.objects.filter(role__role__in=["FAC", "SESS", "COOP"], role__unit=semester_plan.unit)
    capable_instructors = all_instructors.filter(teachingcapability__course__plannedoffering=planned_offering)
    all_instructors = all_instructors.exclude(teachingcapability__course__plannedoffering=planned_offering)

    if request.method == 'POST':
        semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
        course = get_object_or_404(PlannedOffering, slug=planned_offering_slug, plan=semester_plan)

        no_intention_note = "Added by planned administrator. Instructor posted no previous semester teaching intentions."

        instructor_id = request.POST['instructor']
        if instructor_id == "None":
            pre_instructor = course.instructor
            course.instructor = None
            course.save()

            offering_section = course.section[0:2]
            labs = PlannedOffering.objects.filter(plan=semester_plan, course=course.course, component__in=['LAB', 'TUT'], section__startswith=offering_section)
            for lab in labs:
                lab.instructor = None
                lab.save()

            pre_intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=pre_instructor).count()
            pre_teaching_intention = TeachingIntention.objects.get(semester=semester_plan.semester, instructor=pre_instructor)

            if pre_teaching_intention.note == no_intention_note:
                pre_teaching_intention.delete()
            else:
                pre_teaching_intention.intentionfull = (pre_intention_count >= pre_teaching_intention.count)
                pre_teaching_intention.save()

            messages.add_message(request, messages.SUCCESS, 'Instructor removed successfully.')
            return HttpResponseRedirect(reverse(update_plan, kwargs={'semester': semester_plan.semester.name, 'plan_slug': semester_plan.slug}))

        #instructor_id is not None
        assigned_instructor = get_object_or_404(Person, userid=instructor_id)

        if course.instructor:
            pre_instructor = course.instructor
        else:
            pre_instructor = None

        course.instructor = assigned_instructor
        course.save()

        offering_section = course.section[0:2]
        labs = PlannedOffering.objects.filter(plan=semester_plan, course=course.course, component__in=['LAB', 'TUT'], section__startswith=offering_section)
        for lab in labs:
            lab.instructor = assigned_instructor
            lab.save()

        if pre_instructor != None:
            pre_intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=pre_instructor).count()
            pre_teaching_intention = TeachingIntention.objects.get(semester=semester_plan.semester, instructor=pre_instructor)

            if pre_teaching_intention.note == no_intention_note:
                pre_teaching_intention.delete()
            else:
                pre_teaching_intention.intentionfull = (pre_intention_count >= pre_teaching_intention.count)
                pre_teaching_intention.save()

        intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=assigned_instructor).count()
        if TeachingIntention.objects.filter(semester=semester_plan.semester, instructor=assigned_instructor):
            teaching_intentions = TeachingIntention.objects.filter(semester=semester_plan.semester, instructor=assigned_instructor)
            teaching_intention = teaching_intentions[0]

            teaching_intention.intentionfull = (intention_count >= teaching_intentions.count)
            teaching_intention.save()

            messages.add_message(request, messages.SUCCESS, 'Instructor assinged successfully.')
            return HttpResponseRedirect(reverse(update_plan, kwargs={'semester': semester_plan.semester.name, 'plan_slug': semester_plan.slug}))

        else:
            add_intention = TeachingIntention(instructor=assigned_instructor, semester=semester_plan.semester, count=1, intentionfull=True, note=no_intention_note)
            add_intention.save()
            messages.add_message(request, messages.WARNING, 'There is no intention for this instructor.')
            return HttpResponseRedirect(reverse(update_plan, kwargs={'semester': semester_plan.semester.name, 'plan_slug': semester_plan.slug}))

    capable_instructors_list = []
    for i in capable_instructors:
        capable_instructors_list.append({
            'instructor': i,
            'intention': TeachingIntention.objects.filter(instructor=i).order_by('semester'),
            'teachable': TeachingCapability.objects.filter(instructor=i).order_by('course'),
            'current_courses': PlannedOffering.objects.filter(plan=semester_plan, instructor=i, component="LEC")
        })

    all_instructors_list = []
    for i in all_instructors:
        all_instructors_list.append({
            'instructor': i,
            'intention': TeachingIntention.objects.filter(instructor=i).order_by('semester'),
            'teachable': TeachingCapability.objects.filter(instructor=i).order_by('course'),
            'current_courses': PlannedOffering.objects.filter(plan=semester_plan, instructor=i, component="LEC")
        })

    return render(request, "planning/view_instructors.html", {'semester_plan': semester_plan, 'capable_instructors_list': capable_instructors_list, 'all_instructors_list': all_instructors_list, 'planned_offering': planned_offering})
