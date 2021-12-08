from ..db2_query import DB2_Query, Unescaped
from ..semester import Semester, current_semester

import string


class StudentCourseQuery(DB2_Query):
    title = "Student Course Query"
    description = "Fetch a list of students and the courses that they are taking in a semester." 
    query = string.Template("""
    SELECT DISTINCT
        ENRL.EMPLID,
        ENRL.STRM,
        ENRL.REPEAT_CODE,
        ENRL.ACAD_CAREER,
        ENRL.CRSE_GRADE_INPUT,
        CLASS.SUBJECT,
        CLASS.CATALOG_NBR,
        CLASS.DESCR,
        CLASS.CRSE_ID,
        CLASS.EQUIV_CRSE_ID,
        CLASS.ACAD_CAREER AS CLASS_CAREER
    FROM 
        PS_STDNT_ENRL ENRL 
    INNER JOIN 
        PS_CLASS_TBL CLASS 
        ON 
        ENRL.CLASS_NBR = CLASS.CLASS_NBR 
        AND ENRL.STRM = CLASS.STRM
    WHERE 
        ENRL.STDNT_ENRL_STATUS = 'E'
        AND CLASS.CLASS_TYPE = 'E'
        AND ENRL.STRM = $semester
        AND ENRL.CRSE_GRADE_INPUT NOT IN ('AU', 'W', 'WD', 'WE', 'IP', ' ')
    ORDER BY
        ENRL.EMPLID,
        ENRL.STRM
        """)
    # crse_grad_input: 
    # AU - auditing
    # W/WD/WE - withdrawn
    # IP - in progress (should we include these?)
    # FX - transfer credit
    # S - satisfactory
    # ' ' -  No grade...people currently enrolled
    default_arguments = { 'semester': current_semester() }
    
    def __init__(self, query_args):
        for arg in list(StudentCourseQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = StudentCourseQuery.default_arguments[arg]
        self.title = "Student Course Query - " + Semester(query_args["semester"]).long_form()
        super(StudentCourseQuery, self).__init__(query_args)


class SingleCourseQuery(DB2_Query):
    title = "Single Course Query"
    description = "Fetch a list of students who have taken a course."
    query = string.Template("""
    SELECT DISTINCT
        ENRL.EMPLID,
        CLASS.SUBJECT,
        CLASS.CATALOG_NBR
    FROM 
        PS_STDNT_ENRL ENRL 
    INNER JOIN 
        PS_CLASS_TBL CLASS 
        ON 
        ENRL.CLASS_NBR = CLASS.CLASS_NBR 
        AND ENRL.STRM = CLASS.STRM
    WHERE 
        ENRL.EARN_CREDIT = 'Y'
        AND ENRL.STDNT_ENRL_STATUS = 'E'
        AND CLASS.CLASS_TYPE = 'E'
        AND CLASS.SUBJECT = $SUBJECT
        AND CLASS.CATALOG_NBR LIKE '%$catalog_nbr%'
        AND ENRL.CRSE_GRADE_INPUT NOT IN $exclude_list
    ORDER BY
        ENRL.EMPLID
        """)
    exclude_list = ['AU', 'W', 'WD', 'WE']

    default_arguments = {'subject': 'CMPT', 'catalog_nbr': '120', 'exclude_list': exclude_list}
    
    def __init__(self, query_args, include_current=False):
        """
        Runs a query to get every student who has ever taken a given class.

        :param query_args: The arguments that should contain at least the subject and course number
        :type query_args: dict
        :param include_current: A flag to set if you also want to get the students who are currently taking the course.
        :type include_current: bool
        """

        for arg in list(SingleCourseQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = SingleCourseQuery.default_arguments[arg]
        self.title = "Single Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr']
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        # If we passed in the include_current flag, we don't want to exclude people without grades, which are people
        # currently enrolled.  Otherwise, exclude it.
        if not include_current:
            query_args['exclude_list'].append(' ')
        super(SingleCourseQuery, self).__init__(query_args)


class SingleTransferCourseQuery(DB2_Query):
    title = "Single Transfer Course Query"
    description = "Fetch a list of students and whether or not they have taken a single transfer course."
    query = string.Template("""
    SELECT DISTINCT 
        TRANSFER.EMPLID, 
        OFFER.ACAD_GROUP, 
        OFFER.SUBJECT,
        OFFER.CATALOG_NBR
    FROM
        PS_TRNS_CRSE_DTL TRANSFER
    INNER JOIN
        PS_CRSE_OFFER OFFER
    ON 
        TRANSFER.CRSE_ID = OFFER.CRSE_ID AND
        TRANSFER.CRSE_OFFER_NBR = OFFER.CRSE_OFFER_NBR
    WHERE
        OFFER.SUBJECT = $subject
        AND OFFER.CATALOG_NBR LIKE '%$catalog_nbr%'
    """)
    default_arguments = { 'subject': 'CMPT', 'catalog_nbr': '120' }
    
    def __init__(self, query_args):
        for arg in list(SingleTransferCourseQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = SingleTransferCourseQuery.default_arguments[arg]
        self.title = "Single Transfer Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr'] 
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        super(SingleTransferCourseQuery, self).__init__(query_args)


class SingleCourseStrmQuery(DB2_Query):
    title = "Single Course Strm Query"
    description = "Fetch a list of students who have taken a course with matching strm."
    query = string.Template("""
    SELECT DISTINCT
        ENRL.EMPLID,
        CLASS.STRM
    FROM
        PS_STDNT_ENRL ENRL
    INNER JOIN
        PS_CLASS_TBL CLASS
        ON
        ENRL.CLASS_NBR = CLASS.CLASS_NBR
        AND ENRL.STRM = CLASS.STRM
    WHERE
        ENRL.EARN_CREDIT = 'Y'
        AND ENRL.STDNT_ENRL_STATUS = 'E'
        AND CLASS.CLASS_TYPE = 'E'
        AND CLASS.SUBJECT = $subject
        AND CLASS.CATALOG_NBR LIKE '%$catalog_nbr%'
        AND ENRL.CRSE_GRADE_INPUT NOT IN $exclude_list
    ORDER BY
        ENRL.EMPLID
        """)
    exclude_list = ['AU', 'W', 'WD', 'WE']

    default_arguments = {'subject': 'CMPT', 'catalog_nbr': '120', 'exclude_list': exclude_list}

    def __init__(self, query_args, include_current=False):
        """
        Runs a query to get every student who has ever taken a given class and what strm they took it in.
        This is like the SingleCourseQuery, but without the course number (we passed that in, why do we want it
        again?) but with the matching strm, which is needed in one of our reports.

        :param query_args: The arguments that should contain at least the subject and course number
        :type query_args: dict
        :param include_current: A flag to set if you also want to get the students who are currently taking the course.
        :type include_current: bool
        """

        # Add all arguments that are in default_arguments but not in our query_args
        for arg in list(SingleCourseStrmQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = SingleCourseStrmQuery.default_arguments[arg]
        self.title = "Single Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr']
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        # If we passed in the include_current flag, we don't want to exclude people without grades, which are people
        # currently enrolled.  Otherwise, exclude it.
        if not include_current:
            query_args['exclude_list'].append(' ')
        super(SingleCourseStrmQuery, self).__init__(query_args)

class SingleCourseStrmGradeQuery(DB2_Query):
    title = "Single Course Strm Grade Query"
    description = "Fetch a students grade and STRM for a given course and list of emplids."
    query = string.Template("""
    SELECT DISTINCT
        ENRL.EMPLID,
        CLASS.STRM,
        CRSE_GRADE_INPUT
    FROM
        PS_STDNT_ENRL ENRL
    INNER JOIN
        PS_CLASS_TBL CLASS
        ON
        ENRL.CLASS_NBR = CLASS.CLASS_NBR
        AND ENRL.STRM = CLASS.STRM
    WHERE
        ENRL.EARN_CREDIT = 'Y'
        AND ENRL.STDNT_ENRL_STATUS = 'E'
        AND CLASS.CLASS_TYPE = 'E'
        AND CLASS.SUBJECT = $subject
        AND CLASS.CATALOG_NBR LIKE '%$catalog_nbr%'
        AND ENRL.CRSE_GRADE_INPUT NOT IN $exclude_list
        AND ENRL.EMPLID IN $emplids
    ORDER BY
        ENRL.EMPLID, CLASS.STRM
        """)
    exclude_list = ['AU', 'W', 'WD', 'WE']

    default_arguments = {'subject': 'CMPT', 'catalog_nbr': '120', 'exclude_list': exclude_list,
                         'emplids': ['301008183']}

    def __init__(self, query_args, include_current=False):
        """
        Runs a query to get the grades of specified students in a given class and what strm they took it in.

        :param query_args: The arguments that should contain at least the subject and course number
        :type query_args: dict
        :param include_current: A flag to set if you also want to get the students who are currently taking the course.
        :type include_current: bool
        :param emplids:  The list of emplids to query
        :type emplids: list
        """

        # Add all arguments that are in default_arguments but not in our query_args
        for arg in list(SingleCourseStrmGradeQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = SingleCourseStrmGradeQuery.default_arguments[arg]
        self.title = "Single Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr']
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        # If we passed in the include_current flag, we don't want to exclude people without grades, which are people
        # currently enrolled.  Otherwise, exclude it.
        if not include_current:
            query_args['exclude_list'].append(' ')
        super(SingleCourseStrmGradeQuery, self).__init__(query_args)
