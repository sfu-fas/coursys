from courselib.auth import requires_instructor
from django.shortcuts import get_object_or_404, render
from coredata.models import Person, Member
from planning.models import TeachingEquivalent
from fractions import Fraction

def _fraction_display(f):
    whole = int(f)
    remainder = f - int(f)
    s = unicode(whole)
    if remainder > 0:
        s += ' ' + unicode(remainder)
    return s

@requires_instructor
def view_teaching_credits(request):
    """
    Instructors view to see teaching credits
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    members = Member.objects.filter(role='INST', person=instructor)
    equivalents = TeachingEquivalent.objects.filter(instructor=instructor)
    
    semesters = {}
    for member in members:
        offering = member.offering
        course = {'name': offering.name(), 'credits': member.teaching_credit()}
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
    for _, semester in semesters.items():
        credit_count = 0
        for course in semester['courses']:
            credit_count = credit_count + course['credits']
        semester['total_credits'] = _fraction_display(credit_count)
        semester_list.append(semester)
    sorted(semester_list, key=lambda x: x['date_end'])
    
    
    return render(request, 'planning/view_teaching_credits_inst.html', {'semesters': semester_list})
