from ..db2_query import DB2_Query
from ..semester import Semester, current_semester

import string


class GraduatedStudentQuery(DB2_Query):
    title = "Graduated Student Query"
    description = "Given a list of students, fetch a list of graduations." 

    query = string.Template("""
    SELECT DISTINCT
        degree.emplid,
        prog.acad_prog,
        plan.acad_plan,
        degree.completion_term,
        plan.completion_term as PLAN_COMPLETION,
        degree.degree
    FROM 
        ps_acad_degr degree 
    INNER JOIN
        ps_acad_prog prog
        ON 
        prog.emplid = degree.emplid AND
        prog.completion_term = degree.completion_term AND
        prog.acad_prog IN $programs AND 
        prog.prog_action = 'COMP' 
    LEFT JOIN 
        ps_acad_plan plan
        ON
        plan.emplid = degree.emplid
    WHERE 
        degree.completion_term >= $start_semester AND
        degree.completion_term <= $end_semester AND
        degree.emplid in $emplids AND
        plan.COMPLETION_TERM != ''
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

