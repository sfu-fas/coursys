from ..report import Report
from ..table import Table
from ..db2_query import DB2_Query
from ..semester import current_semester
from ..queries.fas_programs import get_fas_programs

from coredata.models import Semester

import string, itertools

INTERNAL_TRANSFER_SLUG = 'apsc-draft-computing-science-internal-transfer-app'


class GenderGroup(DB2_Query):
    title = "Gender breakdown of given emplids"
    description = "Gender breakdown of given emplids"

    query = string.Template("""
        SELECT sex AS gender, count(sex) AS count_internal_transer_applicants
        FROM ps_personal_data
        WHERE emplid IN $emplids
        GROUP BY sex
        """)
    default_arguments = {
        'emplids': ['301008183'],
        }


class CourseWaitlistGendersShort(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT c.subject, c.catalog_nbr, p.sex AS gender, COUNT(*) AS count
                 FROM ps_stdnt_enrl e
                 JOIN ps_class_tbl c
                   ON e.class_nbr=c.class_nbr AND e.strm=c.strm
                 JOIN ps_personal_data p
                   ON e.emplid=p.emplid
                 AND c.class_type='E' AND e.stdnt_enrl_status='W'
                 AND e.strm=$strm AND c.SUBJECT=$subject
                 GROUP BY c.subject, c.catalog_nbr, p.sex
                 ORDER BY c.subject, c.catalog_nbr, p.sex;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class CourseWaitlistGendersFull(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT c.subject, c.catalog_nbr, e.acad_prog, p.sex AS gender, COUNT(*) AS count
                 FROM ps_stdnt_enrl e
                 JOIN ps_class_tbl c
                   ON e.class_nbr=c.class_nbr AND e.strm=c.strm
                 JOIN ps_personal_data p
                   ON e.emplid=p.emplid
                 AND c.class_type='E' AND e.stdnt_enrl_status='W'
                 AND e.strm=$strm AND c.SUBJECT=$subject
                 GROUP BY c.subject, c.catalog_nbr, e.acad_prog, p.sex
                 ORDER BY c.subject, c.catalog_nbr, e.acad_prog, p.sex;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class BadGPAsQuery(DB2_Query):
    # most recent term the student has *actually* taken courses (where we only
    # care about recent strms, so exclude any too old)
    MOST_RECENT_TERM = """
        SELECT emplid, max(strm) as strm
        FROM ps_stdnt_car_term
        WHERE unt_taken_prgrss > 0 AND strm in $strms
        GROUP BY emplid
        """

    # selects students who (in their most recent semester taking courses) were
    # in one of the programs we care about and had a low GPA.
    query = string.Template("""
        SELECT term.acad_prog_primary, p.sex AS gender, term.cum_gpa
        FROM ps_stdnt_car_term term
            JOIN (""" + MOST_RECENT_TERM + """) maxterm
                ON term.emplid=maxterm.emplid AND term.strm=maxterm.strm
            JOIN ps_personal_data p
                ON term.emplid=p.emplid
        WHERE
            term.acad_career='UGRD'
            AND term.acad_prog_primary IN $acad_progs
            AND term.cum_gpa < $gpa
            AND term.tot_taken_gpa > 15
            AND term.withdraw_code='NWD'
        ORDER BY term.acad_prog_primary, p.sex, term.cum_gpa
        """)
    # TODO: I wonder if tot_taken_gpa counts co-op courses. I'd like it to.

    default_arguments = {
        'acad_progs': ('CMPT', 'CMPT2'),
        'strms': ['1174', '1177', '1181'],
        'gpa': '2.4',
        }


class CSGenderExplorationReport(Report):
    title = "CS Gender Exploration"
    description = "What are the different gender breakdowns in CS?"

    def get_transfer_applicants(self):
        # find Persons who have completed the internal transfer form
        from onlineforms.models import Form, SheetSubmission
        try:
            form = Form.objects.get(slug=INTERNAL_TRANSFER_SLUG)
            subsheets = SheetSubmission.objects.filter(sheet__form=form, status='DONE',
                                                       sheet__is_initial=True).select_related('filler',
                                                                                              'filler__sfuFormFiller')
            fillers = {ss.filler.sfuFormFiller.emplid for ss in subsheets if ss.filler.sfuFormFiller}
        except Form.DoesNotExist:
            fillers = {'301008183'}

        # query for their gender
        query = GenderGroup(query_args={'emplids': list(fillers)})
        self.artifacts.append(query.result())

    def get_waitlists(self):
        query = CourseWaitlistGendersShort()
        self.artifacts.append(query.result())
        query = CourseWaitlistGendersFull()
        self.artifacts.append(query.result())

    @staticmethod
    def gpa_bin(gpa):
        if gpa < 2.0:
            return '<2.0'
        elif gpa < 2.2:
            return '2.0+'
        elif gpa < 2.4:
            return '2.2+'
        else:
            return '2.4+'

    @staticmethod
    def group_bin(row):
        return row[0], row[1], CSGenderExplorationReport.gpa_bin(row[2])

    def get_bad_gpa(self):
        current_semester = Semester.current()
        semesters = [current_semester.name, current_semester.offset_name(-1), current_semester.offset_name(-2)]
        cmpt_acad_progs, eng_acad_progs = get_fas_programs()

        cmpt_gpas = BadGPAsQuery(query_args={
            'acad_progs': cmpt_acad_progs,
            'strms': semesters,
            'gpa': '2.4',
        })
        low_gpas = cmpt_gpas.result()
        self.artifacts.append(low_gpas)

        rows = low_gpas.rows
        rows.sort()
        groups = itertools.groupby(rows, CSGenderExplorationReport.group_bin)
        out_rows = [[prog_gpa[0], prog_gpa[1], prog_gpa[2], len(list(students))] for prog_gpa, students in groups]
        bins = Table()
        bins.append_column('ACAD_PROG_PRIMARY')
        bins.append_column('GENDER')
        bins.append_column('GPA')
        bins.append_column('COUNT')
        bins.rows = out_rows
        self.artifacts.append(bins)


    def run(self):
        #self.get_transfer_applicants()
        #self.get_waitlists()
        self.get_bad_gpa()


