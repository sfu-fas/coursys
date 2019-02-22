from coredata.models import Person, Member, Semester
from courselib.auth import requires_instructor
from django.shortcuts import get_object_or_404, render
from fractions import Fraction
from planning.models import TeachingEquivalent
from planning.teaching_equiv_forms import TeachingEquivForm
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

def _fraction_display(f):
    whole = int(f)
    remainder = f - int(f)
    s = str(whole)
    if remainder > 0:
        s += ' ' + str(remainder)
    return s

def _get_teaching_credits_by_semester(instructor):
    members = Member.objects.filter(role='INST', person=instructor)
    equivalents = TeachingEquivalent.objects.filter(instructor=instructor)
    
    semesters = {}
    for member in members:
        offering = member.offering
        course = {'name': offering.name(), 'credits': member.teaching_credit(), 'slug': offering.slug}
        semester = offering.semester
        
        if not semester.label() in semesters:
            semester = {'label': semester.label(), 'date_end': semester.end}
            semester['courses'] = [course]
            semesters[semester['label']] = semester
        else:
            semesters[semester.label()]['courses'].append(course)
            
    for equivalent in equivalents:
        fraction = Fraction(equivalent.credits_numerator, equivalent.credits_denominator)
        name = equivalent.summary
        confirmed = equivalent.status == 'CONF'
        if len(name) > 45:
            name = name[0:45] + "..."
        course = {'name': name, 'credits': fraction, 'equivalent': equivalent.pk, 'confirmed': confirmed}
        semester = equivalent.semester
        
        if not semester.label() in semesters:
            semester = {'label': semester.label(), 'date_end': semester.end}
            semester['courses'] = [course]
            semesters[semester['label']] = semester
        else:
            semesters[semester.label()]['courses'].append(course)
    
    semester_list = []
    for _, semester in list(semesters.items()):
        credit_count = 0
        confirmed = True
        for course in semester['courses']:
            if 'equivalent' in course and not course['confirmed']:
                confirmed = False
            credit_count = credit_count + course['credits']
        semester['total_credits'] = _fraction_display(credit_count)
        semester['confirmed'] = confirmed
        semester_list.append(semester)
        
    semester_list.sort(key=lambda x: x['date_end'], reverse=True)
    return semester_list
    
@requires_instructor
def view_teaching_credits_inst(request):
    """
    Instructors view to see teaching credits
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    semester_list = _get_teaching_credits_by_semester(instructor)
    return render(request, 'planning/view_teaching_credits_inst.html', {'semesters': semester_list})

@requires_instructor
def view_teaching_equivalent_inst(request, equivalent_id):
    """
    Instructors view to see a teaching equivalent
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    equivalent = get_object_or_404(TeachingEquivalent, pk=equivalent_id, instructor=instructor)
    return render(request, 'planning/view_teaching_equiv_inst.html', {'equivalent': equivalent})

@requires_instructor
def new_teaching_equivalent_inst(request):
    """
    Instructors form to create a new teaching equivalent
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = TeachingEquivForm(request.POST)
        if form.is_valid():
            equivalent = form.save(commit=False)
            equivalent.credits_numerator = form.cleaned_data['credits_numerator']
            equivalent.credits_denominator = form.cleaned_data['credits_denominator']
            equivalent.instructor = instructor
            equivalent.status = 'UNCO'
            equivalent.save()
            messages.add_message(request, messages.SUCCESS, "Teaching Equivalent successfully created")
            return HttpResponseRedirect(reverse('planning.views.view_teaching_credits_inst'))
    else:
        form = TeachingEquivForm(initial={'semester': Semester.current().next_semester()})
    return render(request, 'planning/new_teaching_equiv_inst.html', {'form': form})

@requires_instructor
def edit_teaching_equivalent_inst(request, equivalent_id):
    """
    Instructors form to edit a teaching equivalent
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    equivalent = get_object_or_404(TeachingEquivalent, pk=equivalent_id, instructor=instructor, status='UNCO')
    if request.method == 'POST':
        form = TeachingEquivForm(request.POST, instance=equivalent)
        if form.is_valid():
            equivalent = form.save(commit=False)
            equivalent.credits_numerator = form.cleaned_data['credits_numerator']
            equivalent.credits_denominator = form.cleaned_data['credits_denominator']
            equivalent.save()
            messages.add_message(request, messages.SUCCESS, "Teaching Equivalent successfully edited")
            return HttpResponseRedirect(reverse('planning.views.view_teaching_equivalent_inst', kwargs={'equivalent_id': equivalent.id}))
    else:
        credits_value = Fraction("%d/%d" % (equivalent.credits_numerator, equivalent.credits_denominator)).__str__()
        form = TeachingEquivForm(instance=equivalent, initial={'credits': credits_value})
    return render(request, 'planning/edit_teaching_equiv_inst.html', {'form': form, 'equivalent': equivalent})

@requires_instructor
def remove_teaching_equiv_inst(request, equivalent_id):
    """
    Instructors view to remove teaching equivalent
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    if request.method != 'POST':
        raise Http404
    equivalent = get_object_or_404(TeachingEquivalent, pk=equivalent_id, instructor=instructor, status='UNCO')
    equivalent.delete()
    messages.add_message(request, messages.SUCCESS, "Teaching Equivalent successfully removed")
    return HttpResponseRedirect(reverse('planning.views.view_teaching_credits_inst'))
