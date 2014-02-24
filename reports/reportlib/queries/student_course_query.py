from ..db2_query import DB2_Query, Unescaped
from ..semester import Semester, current_semester

import string

class StudentCourseQuery(DB2_Query):
    title = "Student Course Query"
    description = "Fetch a list of students and the courses that they are taking in a semester." 
    query = string.Template("""
    SELECT DISTINCT
        enrl.emplid,
        enrl.strm,
        enrl.repeat_code,
        enrl.acad_career,
        enrl.crse_grade_input,
        class.subject,
        class.catalog_nbr,
        class.descr,
        class.crse_id,
        class.equiv_crse_id,
        class.acad_career as class_career
    FROM 
        ps_stdnt_enrl enrl 
    INNER JOIN 
        ps_class_tbl class 
        ON 
        enrl.class_nbr = class.class_nbr 
        AND enrl.strm = class.strm
    WHERE 
        enrl.stdnt_enrl_status = 'E'
        AND class.class_type = 'E'
        AND enrl.strm = $semester
        AND enrl.crse_grade_input not in ('AU', 'W', 'WD', 'WE', 'IP', ' ')
    ORDER BY
        enrl.emplid,
        enrl.strm
        """)
    # crse_grad_input: 
    # AU - auditing
    # W/WD/WE - withdrawn
    # IP - in progress (should we include these?)
    # FX - transfer credit
    # S - satisfactory
    default_arguments = { 'semester': current_semester() }
    
    def __init__(self, query_args):
        self.title = "Student Course Query - " + Semester(query_args["semester"]).long_form()
        super(StudentCourseQuery, self).__init__(query_args)

class SingleCourseQuery(DB2_Query):
    title = "Single Course Query"
    description = "Fetch a list of students who have taken a course." 
    query = string.Template("""
    SELECT DISTINCT
        enrl.emplid,
        class.subject,
        class.catalog_nbr
    FROM 
        ps_stdnt_enrl enrl 
    INNER JOIN 
        ps_class_tbl class 
        ON 
        enrl.class_nbr = class.class_nbr 
        AND enrl.strm = class.strm
    WHERE 
        enrl.earn_credit = 'Y'
        AND enrl.stdnt_enrl_status = 'E'
        AND class.class_type = 'E'
        AND class.subject = $subject
        AND class.catalog_nbr LIKE '%$catalog_nbr%'
        AND enrl.crse_grade_input not in ('AU', 'W', 'WD', 'WE', ' ')
    ORDER BY
        enrl.emplid
        """)
    default_arguments = { 'subject': 'CMPT', 'catalog_nbr': '120' }
    
    def __init__(self, query_args):
        self.title = "Single Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr'] 
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        super(SingleCourseQuery, self).__init__(query_args)

class SingleTransferCourseQuery(DB2_Query):
    title = "Single Transfer Course Query"
    description = "Fetch a list of students and whether or not they have taken a single transfer course."
    query = string.Template("""
    SELECT DISTINCT 
        transfer.emplid, 
        offer.acad_group, 
        offer.subject,
        offer.catalog_nbr
    FROM
        ps_trns_crse_dtl transfer
    INNER JOIN
        ps_crse_offer offer
    ON 
        transfer.crse_id = offer.crse_id AND
        transfer.crse_offer_nbr = offer.crse_offer_nbr
    WHERE
        offer.subject = $subject
        AND offer.catalog_nbr LIKE '%$catalog_nbr%'
    """)
    default_arguments = { 'subject': 'CMPT', 'catalog_nbr': '120' }
    
    def __init__(self, query_args):
        self.title = "Single Transfer Course Query - " + query_args["subject"] + " " + query_args['catalog_nbr'] 
        query_args['catalog_nbr'] = Unescaped(query_args['catalog_nbr'])
        super(SingleTransferCourseQuery, self).__init__(query_args)

