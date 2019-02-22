from courselib.auth import requires_role
from django.http import HttpResponse
from coredata.models import Semester, Unit
from grad.models import GradStudent, CompletedRequirement, Supervisor, Scholarship, OtherFunding, GradStatus
from ta.models import TACourse
from ra.models import RAAppointment
from coredata.queries import grad_student_courses, grad_student_gpas

# This view is for generating the SQL queries needed to push our data
#   into the CMPT Progress Reports system.
#   It doesn't have anything to do with the management of the 
#   Progress Reports objects. 

def escape(s):
    if s is None:
        return 'null'
    elif type(s) in (int,int,float):
        return(s)
    else:
        import MySQLdb
        if type(s)==str:
            return "'" + MySQLdb._mysql.escape_string(s) + "'"
        else:
            return "'" + MySQLdb._mysql.escape_string(str(s,errors='replace')) + "'"

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


def generate_people_queries(gs):
    """
    Generate queries for the people database
    """
    # personal info
    yield ("INSERT INTO people.person (emplid, LegalGivenNames, PreferredGivenNames, PreferredSurnames, Title, sex, "
            + "ShowProfile, ShowPicture, Note, LegalSurnames)\n    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            + "\n    ON DUPLICATE KEY UPDATE "
            + "Title=%s, LegalGivenNames=%s, PreferredGivenNames=%s, LegalSurnames=%s, Sex=%s;\n") \
            % escape_all(gs.person.emplid, gs.person.first_name, gs.person.pref_first_name, gs.person.last_name,
                     gs.person.get_title(), gs.person.gender(), 'n', 'n', '', gs.person.last_name,
                     gs.person.get_title(), gs.person.first_name, gs.person.pref_first_name, gs.person.last_name, gs.person.gender())
    yield ("INSERT INTO people.Email (emplid, Type, EmailAddress, PreferredFlag) VALUES "
        + "(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
        + "emplid=%s;\n") \
        % escape_all(gs.person.emplid, 'acs', gs.person.email(), 1, gs.person.emplid)
    yield ("INSERT INTO people.GradStudent (emplid, SIN, Department) VALUES (%s, %s, %s) "
         + "ON DUPLICATE KEY UPDATE StartSemester=%s, EndSemester=%s;\n") \
        % escape_all(gs.person.emplid, gs.person.sin(), gs.program.unit.label, gs.start_semester.name, gs.end_semester.name if gs.end_semester else None)
    yield ("INSERT INTO people.PersonRole (emplid, RoleId, Type, Blurb) VALUES (%s, %s, %s, %s) "
         + "ON DUPLICATE KEY UPDATE emplid=%s;\n") \
        % escape_all(gs.person.emplid, 11, 1, '', gs.person.emplid)
    
    # program
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

    # supervisory committee
    yield "DELETE FROM people.Supervisor WHERE StudentId=%s;\n" % escape_all(gs.person.emplid)
    yield "DELETE FROM people.SupervisorExternal WHERE emplid=%s;\n" % escape_all(gs.person.emplid)
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


def generate_progrep_queries(gs):
    """
    Generate queries for the progrep database
    """
    # funding
    yield "DELETE FROM progrep.finsupport WHERE emplid=%s;\n" % escape_all(gs.person.emplid)
    ta_courses = TACourse.objects.filter(contract__application__person=gs.person, contract__status='SGN') \
                 .select_related('contract__posting__semester')
    for tacrs in ta_courses:
        yield ("INSERT INTO progrep.finsupport (emplid, semester, type, name, amount, bu) VALUES (%s, %s, %s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, tacrs.contract.posting.semester.name, 'ta', tacrs.course.name(), "%.2f"%tacrs.pay(), int(tacrs.bu))

    ras = RAAppointment.objects.filter(person=gs.person, deleted=False)
    for ra in ras:
        yield ("INSERT INTO progrep.finsupport (emplid, semester, type, name, amount, bu) VALUES (%s, %s, %s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, ra.start_semester().name, 'ra', ra.hiring_faculty.name(), "%.2f"%ra.lump_sum_pay, '')

    scholarships = Scholarship.objects.filter(student=gs, removed=False)
    for schol in scholarships:
        yield ("INSERT INTO progrep.finsupport (emplid, semester, type, name, amount, bu) VALUES (%s, %s, %s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, schol.start_semester.name, 'scholarship', schol.scholarship_type.name, "%.2f"%schol.amount, '')

    otherfunding = OtherFunding.objects.filter(student=gs, removed=False)
    for other in otherfunding:
        yield ("INSERT INTO progrep.finsupport (emplid, semester, type, name, amount, bu) VALUES (%s, %s, %s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, other.semester.name, 'other', other.description, "%.2f"%other.amount, '')

    sessionals = gs.sessional_courses()
    for offering in sessionals:
        yield ("INSERT INTO progrep.finsupport (emplid, semester, type, name, amount, bu) VALUES (%s, %s, %s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, offering.semester.name, 'sessional', offering.name(), "%.2f"%offering.sessional_pay(), '')
        

    # grades & GPA
    for coursedata in grad_student_courses(gs.person.emplid):
        strm, subject, number, section, units, grade, gradepoints, instr = coursedata
        yield ("INSERT INTO progrep.grade (emplid, semester, course_dept, course_num, course_section,"
               + "credits, grade, grade_point, breadth_area, faculty)\n    VALUES "
               + "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)\n    ON DUPLICATE KEY UPDATE "
               + "credits=%s, grade=%s, grade_point=%s;\n") \
            % escape_all(gs.person.emplid, strm, subject, number, section, units, grade, gradepoints, '', instr,
                         units, grade, gradepoints)
       
    yield "DELETE FROM progrep.gpa WHERE emplid=%s;\n" % escape_all(gs.person.emplid)
    for strm, sgpa, cgpa in grad_student_gpas(gs.person.emplid):
        yield ("INSERT INTO progrep.gpa (emplid, semester, SGPA, CGPA) VALUES "
               + "(%s, %s, %s, %s);\n") \
            % escape_all(gs.person.emplid, strm, sgpa, cgpa)

    # leaves
    statuses = GradStatus.objects.filter(student=gs, status='LEAV', hidden=False)
    for st in statuses:
        yield ("INSERT INTO progrep.onleave (emplid, semester, reason) VALUES "
               + "(%s, %s, %s) ON DUPLICATE KEY UPDATE emplid=%s, semester=%s;\n") \
            % escape_all(gs.person.emplid, st.start.name, '', gs.person.emplid, st.start.name)
    
    # user accounting
    yield ("INSERT INTO progrep.user (emplid, username, email_notifications, final_email) VALUES "
               + "(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE emplid=%s;\n") \
            % escape_all(gs.person.emplid, gs.person.userid, 'Y', 'Y', gs.person.emplid)
    yield ("INSERT INTO progrep.user_role (emplid, role_id) VALUES "
               + "(%s, %s) ON DUPLICATE KEY UPDATE emplid=%s;\n") \
            % escape_all(gs.person.emplid, 1, gs.person.emplid)


def generate_queries(notes, grads):
    """
    Generate all of the queries that need to be fired to get the Progress Reports database updated.
    """
    for n in notes:
        yield "# " + n + "\n"

    for gs in grads:
        yield '\n# %s %s (%s)\n' % (gs.person.name(), gs.program.description, gs.person.emplid)
        yield "START TRANSACTION;\n"
        for q in generate_people_queries(gs):
            yield q
        yield "\n"
        for q in generate_progrep_queries(gs):
            yield q
        yield "COMMIT;\n"





@requires_role("GRAD", get_only=["GRPD"])
def progress_reports(request):
    last_semester = Semester.current().previous_semester()
    CS_UNIT=Unit.objects.get(label='CMPT')
    grads = GradStudent.objects.filter(program__unit=CS_UNIT, start_semester__name__lte=last_semester.name,
    #grads = GradStudent.objects.filter(program__unit__in=request.units, start_semester__name__lte=last_semester.name,
                end_semester=None, current_status__in=['ACTI', 'LEAV', 'PART']) \
                .select_related('person', 'program__unit').order_by('person')
    #grads = grads[:50]
    query_text = generate_queries(['queried students starting in %s or before: %i students'%(last_semester.name, grads.count())], grads)
    query_text = ''.join(query_text)
    return HttpResponse(query_text, content_type='text/plain')
