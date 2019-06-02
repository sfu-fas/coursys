from ..report import Report
from ..queries.fas_programs import get_fas_programs
from ..queries.progress_queries import InternationalGPAQuery, AdvisorVisits, AdvisorNotes
from coredata.models import Semester
import string


class InternationalGPAReport(Report):
    title = "GPA for FAS students with visa/citizenship"
    description = "GPA for FAS students with visa/citizenship"

    def run(self):
        cmpt_progs, eng_progs = get_fas_programs()
        fas_progs = cmpt_progs + eng_progs

        # collect student data for every semester in the last year.
        # Do it here because I'm not smart enough to do it in SQL.
        semester = Semester.current()
        last_yr = [semester.offset_name(-2), semester.offset_name(-1), semester.name]
        student_data = {}
        for strm in last_yr:
            students = InternationalGPAQuery({
                'acad_progs': fas_progs,
                'strm': strm,
            }).result()

            for r in students.rows:
                emplid = r[0]
                student_data[emplid] = r

        students.rows = list(student_data.values())

        visits = AdvisorVisits(unit_slugs=['apsc']).result()
        notes = AdvisorNotes(unit_slugs=['apsc']).result()

        students.left_join(visits, 'EMPLID')
        students.left_join(notes, 'EMPLID')
        self.artifacts.append(students)

