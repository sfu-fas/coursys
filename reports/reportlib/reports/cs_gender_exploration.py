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
        SELECT SEX AS GENDER, COUNT(SEX) AS COUNT_INTERNAL_TRANSER_APPLICANTS
        FROM PS_PERSONAL_DATA
        WHERE EMPLID IN $emplids
        GROUP BY SEX
        """)
    default_arguments = {
        'emplids': ['301008183'],
        }


class CourseWaitlistGendersShort(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT C.SUBJECT, C.CATALOG_NBR, P.SEX AS GENDER, COUNT(*) AS COUNT
                 FROM PS_STDNT_ENRL E
                 JOIN PS_CLASS_TBL C
                   ON E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM
                 JOIN PS_PERSONAL_DATA P
                   ON E.EMPLID=P.EMPLID
                 AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='W'
                 AND E.STRM=$strm AND C.SUBJECT=$subject
                 GROUP BY C.SUBJECT, C.CATALOG_NBR, P.SEX
                 ORDER BY C.SUBJECT, C.CATALOG_NBR, P.SEX;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class CourseWaitlistGendersFull(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT C.SUBJECT, C.CATALOG_NBR, E.ACAD_PROG, P.SEX AS GENDER, COUNT(*) AS COUNT
                 FROM PS_STDNT_ENRL E
                 JOIN PS_CLASS_TBL C
                   ON E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM
                 JOIN PS_PERSONAL_DATA P
                   ON E.EMPLID=P.EMPLID
                 AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='W'
                 AND E.STRM=$strm AND C.SUBJECT=$subject
                 GROUP BY C.SUBJECT, C.CATALOG_NBR, E.ACAD_PROG, P.SEX
                 ORDER BY C.SUBJECT, C.CATALOG_NBR, E.ACAD_PROG, P.SEX;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class BadGPAsQuery(DB2_Query):
    # most recent term the student has *actually* taken courses (where we only
    # care about recent strms, so exclude any too old)
    MOST_RECENT_TERM = """
        SELECT EMPLID, MAX(STRM) AS STRM
        FROM PS_STDNT_CAR_TERM
        WHERE UNT_TAKEN_PRGRSS > 0 AND STRM IN $strms
        GROUP BY EMPLID
        """

    # selects students who (in their most recent semester taking courses) were
    # in one of the programs we care about and had a low GPA.
    query = string.Template("""
        SELECT TERM.ACAD_PROG_PRIMARY, P.SEX AS GENDER, TERM.CUM_GPA
        FROM PS_STDNT_CAR_TERM TERM
            JOIN (""" + MOST_RECENT_TERM + """) MAXTERM
                ON TERM.EMPLID=MAXTERM.EMPLID AND TERM.STRM=MAXTERM.STRM
            JOIN PS_PERSONAL_DATA P
                ON TERM.EMPLID=P.EMPLID
        WHERE
            TERM.ACAD_CAREER='UGRD'
            AND TERM.ACAD_PROG_PRIMARY IN $acad_progs
            AND TERM.CUM_GPA < $gpa
            AND TERM.TOT_TAKEN_GPA > 15
            AND TERM.WITHDRAW_CODE='NWD'
        ORDER BY TERM.ACAD_PROG_PRIMARY, P.SEX, TERM.CUM_GPA
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
        self.get_transfer_applicants()
        self.get_waitlists()
        self.get_bad_gpa()


