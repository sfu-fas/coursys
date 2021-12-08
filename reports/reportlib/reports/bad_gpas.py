from ..report import Report
from ..queries import EmailQuery, NameQuery
from ..queries.fas_programs import get_fas_programs
from ..db2_query import DB2_Query
from coredata.models import Semester
import string



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
        SELECT TERM.EMPLID, TERM.ACAD_PROG_PRIMARY, TERM.STRM AS LAST_STRM, TERM.CUM_GPA, TERM.TOT_PASSD_GPA AS SFU_CREDITS
        FROM PS_STDNT_CAR_TERM TERM
            JOIN (""" + MOST_RECENT_TERM + """) MAXTERM
            ON TERM.EMPLID=MAXTERM.EMPLID AND TERM.STRM=MAXTERM.STRM
        WHERE
            TERM.ACAD_CAREER='UGRD'
            AND TERM.ACAD_PROG_PRIMARY IN $acad_progs
            AND TERM.CUM_GPA < $gpa
            AND TERM.TOT_TAKEN_GPA > 15
            AND TERM.WITHDRAW_CODE='NWD'
        """)
    # TODO: I wonder if tot_taken_gpa counts co-op courses. I'd like it to.

    default_arguments = {
        'acad_progs': ('CMPT', 'CMPT2'),
        'strms': ['1147', '1151'],
        'gpa': '2.4',
        }


class BadGPAsReport(Report):
    title = "FAS students with GPAs below continuation"
    description = "Students with bad GPAs who need attention from the advisors"

    def bad_gpa_for(self, acad_progs, semesters, gpa):
        bad_gpa = BadGPAsQuery(query_args={
            'acad_progs': acad_progs,
            'strms': semesters,
            'gpa': gpa,
        }).result()
        #bad_gpa.compute_column('GPA', lambda r: unicode(r['CUM_GPA']))
        #bad_gpa.remove_column('CUM_GPA')
        #bad_gpa.flatten('EMPLID')

        return bad_gpa



    def run(self):
        current_semester = Semester.current()
        semesters = [current_semester.name, current_semester.offset_name(-1), current_semester.offset_name(-2)]

        cmpt_acad_progs, eng_acad_progs = get_fas_programs()

        cmpt_gpas = self.bad_gpa_for(cmpt_acad_progs, semesters, '2.4')
        eng_gpas = self.bad_gpa_for(eng_acad_progs, semesters, '2.5')

        bad_gpas = cmpt_gpas
        for r in (eng_gpas.rows):
            bad_gpas.append_row(r)

        name_query = NameQuery()
        names = name_query.result()

        email_query = EmailQuery()
        email = email_query.result()
        email.filter( EmailQuery.preferred_email )

        bad_gpas.left_join( names, "EMPLID" )
        bad_gpas.left_join( email, "EMPLID" )

        bad_gpas.remove_column('E_ADDR_TYPE')
        bad_gpas.remove_column('PREF_EMAIL_FLAG')

        self.artifacts.append(bad_gpas)
