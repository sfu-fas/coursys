from ..db2_query import DB2_Query
from ..semester import Semester, current_semester

import string


class GraduatedStudentQuery(DB2_Query):
    title = "Graduated Student Query"
    description = "Given a list of students, fetch a list of graduations." 

    query = string.Template("""
    SELECT DISTINCT
        DEGREE.EMPLID,
        PROG.ACAD_PROG,
        APLAN.ACAD_PLAN,
        DEGREE.COMPLETION_TERM,
        APLAN.COMPLETION_TERM AS PLAN_COMPLETION,
        DEGREE.DEGREE
    FROM 
        PS_ACAD_DEGR DEGREE 
    INNER JOIN
        PS_ACAD_PROG PROG
        ON 
        PROG.EMPLID = DEGREE.EMPLID AND
        PROG.COMPLETION_TERM = DEGREE.COMPLETION_TERM AND
        PROG.ACAD_PROG IN $programs AND 
        PROG.PROG_ACTION = 'COMP' 
    LEFT JOIN 
        PS_ACAD_PLAN APLAN
        ON
        APLAN.EMPLID = DEGREE.EMPLID
    WHERE 
        DEGREE.COMPLETION_TERM >= $start_semester AND
        DEGREE.COMPLETION_TERM <= $end_semester AND
        DEGREE.EMPLID IN $emplids AND
        APLAN.COMPLETION_TERM != ''
        """)

    default_arguments = {
        'start_semester': str(current_semester().increment(-3)),
        'end_semester': str(current_semester()),
        'programs': ['CMPT'],
        'emplids': ['301008183', '301050395']
        }
    
    def __init__(self, query_args):
        """
        Run a query to get every completed graduation given a list of students and programs.

        :param query_args:  The arguments that should contain programs and students, and, optionally, start and end semesters.
        :type query_args: dict
        """
        # Add all arguments that are in default_arguments but not in our query_args
        for arg in list(GraduatedStudentQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = GraduatedStudentQuery.default_arguments[arg]
        self.title = "Graduated Student Query - " + \
            Semester(query_args["start_semester"]).long_form() + " to " + \
            Semester(query_args["end_semester"]).long_form()
        super(GraduatedStudentQuery, self).__init__(query_args)

