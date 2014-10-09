from ..report import Report
from ..queries import program_and_plan


class BadGPAsReport(Report):
    title = "FAS students with GPAs below continuation"
    description = "Students with bad GPAs who need attention from the advisors"

    def run(self):
        cmpt_progs = program_and_plan.AcadProgsOwnedByUnit(
                query_args={'acad_org':  'COMP SCI'}).result()
        self.artifacts.append(cmpt_progs)
