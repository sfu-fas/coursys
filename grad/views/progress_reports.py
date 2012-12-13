from courselib.auth import requires_role
from django.http import HttpResponse
from coredata.models import Semester
from grad.models import GradStudent, CompletedRequirement, Supervisor
import MySQLdb

def escape(s):
    if s is None:
        return 'null'
    elif type(s) == int:
        return unicode(s)
    else:
        return "'" + MySQLdb._mysql.escape_string(unicode(s)) + "'"

def escape_all(*ss):
    return tuple(map(escape, ss))

def export_status(st):
    """
    Status in the way cortez expects it
    """
    if st == 'ACTI':
        return 'a'
    elif st == 'LEAV':
        return 'o'
    elif st == 'GRAD':
        return 'g'
    elif st == 'WIDR':
        return 'w'
    else:
        return 'u'

requirements = ['Supervisory Committee', 'Breadth Requirements', 'Research Topic', 'Depth Exam', 'Thesis Proposal', 'Thesis Defence']
def completed_statuses(gs):
    """
    Build the list of requirement completion semesters in the "right" order.
    """
    res = []
    for req_name in requirements:
        reqs = CompletedRequirement.objects.filter(student=gs, requirement__description=req_name)
        if reqs:
            req = reqs[0]
            res.append(req.semester.name)
        else:
            res.append(None)
    return res


def generate_queries(notes, grads):
    for n in notes:
        yield "# " + n + "\n"

    yield '\n# people.person entries\n'
    for gs in grads:
        yield ("INSERT INTO people.person (emplid, LegalGivenNames, PreferredGivenNames, PreferredSurnames, Title, sex, "
            + "ShowProfile, ShowPicture, Note, LegalSurnames)\n    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            + "\n    ON DUPLICATE KEY UPDATE "
            + "Title=%s, LegalGivenNames=%s, PreferredGivenNames=%s, LegalSurnames=%s, Sex=%s;\n") \
            % escape_all(gs.person.emplid, gs.person.first_name, gs.person.pref_first_name, gs.person.last_name,
                     gs.person.get_title(), gs.person.gender(), 'n', 'n', '', gs.person.last_name,
                     gs.person.get_title(), gs.person.first_name, gs.person.pref_first_name, gs.person.last_name, gs.person.gender())

    yield '\n# people.Email entries\n'
    for gs in grads:
        yield ("INSERT INTO people.Email (emplid, Type, EmailAddress, PreferredFlag) VALUES "
        + "(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
        + "emplid=%s;\n") \
        % escape_all(gs.person.emplid, 'acs', gs.person.email(), 1, gs.person.emplid)
    
    yield '\n# people.GradStudent entries\n'
    for gs in grads:
        yield ("INSERT INTO people.GradStudent (emplid, SIN, Department) VALUES (%s, %s, %s) "
         + "ON DUPLICATE KEY UPDATE StartSemester=%s, EndSemester=%s;\n") \
        % escape_all(gs.person.emplid, gs.person.sin(), gs.program.unit.label, gs.start_semester.name, gs.end_semester.name if gs.end_semester else None)

    yield '\n# people.PersonRole entries\n'
    for gs in grads:
        yield ("INSERT INTO people.PersonRole (emplid, RoleId, Type, Blurb) VALUES (%s, %s, %s, %s) "
         + "ON DUPLICATE KEY UPDATE emplid=%s;\n") \
        % escape_all(gs.person.emplid, 11, 1, '', gs.person.emplid)
    
    yield '\n# people.GradStudentProgram entries\n'
    for gs in grads:
        prog, ptype = gs.program.cmpt_program_type()
        statuses = completed_statuses(gs)
        yield ("INSERT INTO people.GradStudentProgram SET emplid=%s, GradProgram=%s, GradDegreeType=%s, Status=%s, "
         + "StartSemester=%s, EndSemester=%s,\n    ResearchArea=%s, "
         + "CommitteeSelected=%s, Breadth=%s, TopicChosen=%s, DepthExam=%s, ProposalCompleted=%s, ThesisDefended=%s"
         + "\n    ON DUPLICATE KEY UPDATE GradProgram=%s, GradDegreeType=%s, Status=%s, "
         + "StartSemester=%s, EndSemester=%s,\n    ResearchArea=%s, "
         + "CommitteeSelected=%s, Breadth=%s, TopicChosen=%s, DepthExam=%s, ProposalCompleted=%s, ThesisDefended=%s;\n") \
        % (escape_all(gs.person.emplid, prog, ptype, export_status(gs.current_status), gs.start_semester.name, gs.end_semester.name if gs.end_semester else None,
                     gs.research_area) + escape_all(*statuses) + escape_all(prog, ptype, export_status(gs.current_status), gs.start_semester.name, gs.end_semester.name if gs.end_semester else None,
                     gs.research_area) + escape_all(*statuses))

    yield '\n# people.Supervisor[External] entries\n'
    for gs in grads:
        yield "DELETE FROM people.Supervisor WHERE StudentId=%s;\n" % escape_all(gs.person.emplid)
        yield "DELETE FROM people.SupervisorExternal WHERE emplid=%s;\n" % escape_all(gs.person.emplid)

        prog, ptype = gs.program.cmpt_program_type()
        statuses = completed_statuses(gs)

        seniors = Supervisor.objects.filter(student=gs, removed=False, supervisor_type='SEN').count()
        superv = Supervisor.objects.filter(student=gs, removed=False, supervisor_type__in=['SEN', 'COM', 'POT'])
        superv = list(superv)
        superv.sort(cmp=lambda x,y: cmp(x.type_order(), y.type_order()))
        
        for i,sup in enumerate(superv):
            st = 'a'
            if sup.supervisor_type == 'POT' and seniors > 0:
                st = 'i'
            if sup.supervisor: # internal supervisor
                yield ("INSERT INTO people.Supervisor (emplid, StudentID, GradProgram, GradDegreeType, Status, Priority, NumberOfSeniorSup) "
                       + "\n    VALUES (%s, %s, %s, %s, %s, %s, %s);\n") \
                % escape_all(sup.supervisor.emplid, gs.person.emplid, prog, ptype, st, i+1, seniors)
            else: # external
                yield ("INSERT INTO people.SupervisorExternal (emplid, Supervisor, GradProgram, GradDegreeType) "
                       + "VALUES (%s, %s, %s, %s);\n") \
                % escape_all(gs.person.emplid, sup.external, prog, ptype)



@requires_role("GRAD", get_only=["GRPD"])
def progress_reports(request):
    last_semester = Semester.current().previous_semester()

    grads = GradStudent.objects.filter(program__unit__in=request.units, start_semester__name__lte=last_semester.name,
                end_semester=None, current_status__in=['ACTI', 'LEAV', 'PART']) \
                .select_related('person', 'program__unit')
    query_text = generate_queries(['queried students starting in %s or before'%(last_semester.name)], grads)
    query_text = ''.join(query_text)
    return HttpResponse(query_text, mimetype='text/plain')
