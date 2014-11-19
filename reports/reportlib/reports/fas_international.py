from ..report import Report
from ..queries.fas_programs import get_fas_programs
from ..queries.progress_queries import InternationalGPAQuery, AdvisorVisits, AdvisorNotes
from coredata.models import Semester
import string


class InternationalGPAReport(Report):
    title = "GPA for FAS students with visa/citizenship"
    description = "GPA for FAS students with visa/citizenship"

    def run(self):
        current_semester = Semester.current()
        cmpt_progs, eng_progs = get_fas_programs()
        fas_progs = cmpt_progs + eng_progs

        students = InternationalGPAQuery({
            'acad_progs': fas_progs,
            'strm': current_semester.name,
        }).result()

        visits = AdvisorVisits(unit_slugs=['apsc']).result()
        notes = AdvisorNotes(unit_slugs=['apsc']).result()

        students.left_join(visits, 'EMPLID')
        students.left_join(notes, 'EMPLID')
        self.artifacts.append(students)

