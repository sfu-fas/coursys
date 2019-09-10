from reports.reportlib.report import Report
from reports.reportlib.table import Table
from grad.models import GradStudent, GradProgram, GradRequirement, CompletedRequirement, Supervisor
from coredata.models import Semester


class CMPTGradRequirementsReport(Report):
    """
    Dataset 1: All active PhDs in CMPT who are in semester 3 or more who do not have requirement "Supervisor Committee"
    Dataset 2: All active PhDs in CMPT who are in semester 6 or more who have neither of "Depth Exam" or
    "Breadth Requirements" requirements
    Dataset 3: All active PhDs in CMPT who are in semester 9 or more who do not have all of "Depth Exam", "Breadth
    Requirements", and "Thesis Proposal"

    Output: 3 Tables representing each dataset.
    Name, Student ID, Email, Semester Count, Senior supervisor name + email, and for table 3, which requirement(s)
    is(are) missing.
    """
    title = "CMPT Grad Requirements Report"
    description = "This report shows which grad students haven't met particular requirements at a given time."

    def run(self):
        current_semester = Semester.current()

        # Get all active CMPT PhD students, since that's all we care about.
        program = GradProgram.objects.get(label="PhD", unit__label='CMPT')
        all_students = GradStudent.objects.filter(program=program, current_status='ACTI')
        senior_supervisors = Supervisor.objects.filter(student__in=all_students, supervisor_type='SEN', removed=False)
        potential_supervisors = Supervisor.objects.filter(student__in=all_students, supervisor_type='POT', removed=False)

        # Split them up between the 3 tables we want:
        table1_students = all_students.filter(start_semester__lte=current_semester.offset(-2))
        table2_students = all_students.filter(start_semester__lte=current_semester.offset(-5))
        table3_students = all_students.filter(start_semester__lte=current_semester.offset(-8))

        # The GradRequirements we care about:
        requirement1 = GradRequirement.objects.get(program=program, description='Supervisory Committee')
        requirement2 = GradRequirement.objects.get(program=program, description='Depth Exam')
        requirement3 = GradRequirement.objects.get(program=program, description='Breadth Requirements Approved')
        requirement4 = GradRequirement.objects.get(program=program, description='Thesis Proposal')

        # All three tables will have the same columns, might as well create them quickly.
        table1 = Table()
        table2 = Table()
        table3 = Table()
        for table in [table1, table2, table3]:
            table.append_column("Name")
            table.append_column("Student ID")
            table.append_column("Email")
            table.append_column("Semester Count")
            table.append_column("Senior Supervisor")
        table3.append_column("Missing Requirement(s)")

        # A quick helper method to build the string to display for the Senior Supervisor, given a student
        def get_supervisor_string(student):
            supervisor = senior_supervisors.filter(student=student).first()
            if supervisor:
                return '%s <%s>' % (supervisor.supervisor.name(), supervisor.supervisor.email())
            else:
                supervisor = potential_supervisors.filter(student=student).first()
                if supervisor:
                    return '%s (potential) <%s>' % (supervisor.supervisor.name(), supervisor.supervisor.email())
                else:
                    return 'None'


        # Get the lists of students from the master list who have completed the various requirements.
        students1_completed = CompletedRequirement.objects.values_list('student', flat=True)\
            .filter(requirement=requirement1, student__in=all_students, removed=False)
        students2_completed = CompletedRequirement.objects.values_list('student', flat=True) \
            .filter(requirement=requirement2, student__in=all_students, removed=False)
        students3_completed = CompletedRequirement.objects.values_list('student', flat=True) \
            .filter(requirement=requirement3, student__in=all_students, removed=False)
        # The 4th requirement only really applies to the third list, so might as well limit it:
        students4_completed = CompletedRequirement.objects.values_list('student', flat=True) \
            .filter(requirement=requirement3, student__in=table3_students, removed=False)

        #  First table, simply everyone in table1_students who doesn't have a completed requirement 1
        for student in [s for s in table1_students if s.id not in students1_completed]:
            supervisor_string = get_supervisor_string(student)
            table1.append_row([student.person.name(), student.person.emplid, student.person.email(),
                              current_semester - student.start_semester + 1, supervisor_string])

        #  Table 2 is also pretty easy, just add everyone who is is missing both of requirements 2 & 3.
        for student in [s for s in table2_students if s.id not in students2_completed and
                                                      s.id not in students3_completed]:
            supervisor_string = get_supervisor_string(student)
            table2.append_row([student.person.name(), student.person.emplid, student.person.email(),
                              current_semester - student.start_semester + 1, supervisor_string])

        # Table 3 will require a bit more work, since we want to also display what requirements aren't met.
        # First, establish our target students:
        students3 = [s for s in table3_students if s.id not in students2_completed or s.id not in students3_completed
                     or s.id not in students4_completed]
        for student in students3:
            #  Build the string telling us which requirement is missing.  Stupid, but has to be done.
            missing_str_list = []
            requirement_to_list = [(requirement2, students2_completed), (requirement3, students3_completed),
                                   (requirement4, students4_completed)]
            for requirement, student_list in requirement_to_list:
                if student.id not in student_list:
                    missing_str_list.append(requirement.description)
            missing_str = '; '.join(missing_str_list)
            supervisor_string = get_supervisor_string(student)
            table3.append_row([student.person.name(), student.person.emplid, student.person.email(),
                              current_semester - student.start_semester + 1, supervisor_string, missing_str])

        for table in [table1, table2, table3]:
            self.artifacts.append(table)
