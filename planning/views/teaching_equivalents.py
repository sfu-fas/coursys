from courselib.auth import requires_instructor
from django.shortcuts import get_object_or_404, render
from coredata.models import Person, Member

@requires_instructor
def view_teaching_credits(request):
    """
    Instructors view to see teaching credits
    """
    instructor = get_object_or_404(Person, userid=request.user.username)
    members = Member.objects.filter(role='INST', person=instructor)
    
    semesters = {}
    for member in members:
        offering = member.offering
        course = {'name': offering.name(), 'credits': member.teaching_credit_str()}
        semester = offering.semester
        
        if not semester.label() in semesters:
            semester = {'label': semester.label(), 'date_end': semester.end}
            semester['courses'] = [course]
            semesters[semester['label']] = semester
        else:
            semesters[semester.label()]['courses'].append(course)
    
    return render(request, 'planning/view_teaching_credits_inst.html', {'semesters': semesters})