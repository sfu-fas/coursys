from ..db2_query import DB2_Query
from ..semester import current_semester
import string

class CGPAQuery(DB2_Query):
    title = "Calculated GPA Query"
    description = "Fetch a complete list of pre-calculated student-to-GPA mappings by semester" 

    query = string.Template("""
    SELECT DISTINCT 
        emplid,
        cum_gpa,
        tot_passd_prgrss AS CREDITS
    FROM 
        ps_stdnt_car_term
    WHERE 
        strm = $semester
        """)
    default_arguments = {
        'semester': current_semester()
        }

class GPA_Query(DB2_Query):
    title = "Computed GPA Query"
    description = "Compute a list of student-to-GPA mappings"

    query = string.Template("""
    SELECT DISTINCT
        emplid,
        SUM( e.grade_points )/SUM( e.unt_taken ) as CGPA
    FROM 
        ps_stdnt_enrl e
    WHERE
        e.acad_career='UGRD' AND
        e.stdnt_enrl_status='E' AND
        e.include_in_gpa='Y' AND
        e.crse_grade_off <> ' ' AND
        e.emplid in $emplids
    GROUP BY emplid
    """)
    default_arguments = { 'emplids': ['301008183'] }

class UDGPA_Query(DB2_Query):
    title = "Computed UDGPA Query"
    description = "Compute a list of student-to-UDGPA mappings. "

    query = string.Template("""
    SELECT DISTINCT
        emplid,
        SUM( e.grade_points )/SUM( e.unt_taken ) as UDGPA
    FROM
        ps_stdnt_enrl e
    WHERE
        e.acad_career='UGRD' AND
        e.stdnt_enrl_status='E' AND
        e.include_in_gpa='Y' AND
        e.crse_grade_off <> ' ' AND
        e.emplid in $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                ps_class_tbl c
            WHERE
                e.strm = c.strm AND
                e.class_nbr = c.class_nbr AND
                c.catalog_nbr >= ' 300' AND
                c.catalog_nbr <= ' 499' 
        )
    GROUP BY emplid
        
    """)
    default_arguments = { 'emplids': ['301008183'] }

class Subject_UDGPA_Query(DB2_Query):
    title = "Subject UDGPA Query"
    description = "Compute a list of student-to-UDGPA mappings for courses in a specific subject. "

    query = string.Template("""
    SELECT DISTINCT
        emplid,
        SUM( e.grade_points )/SUM( e.unt_taken ) as SUBJECT_UDGPA
    FROM
        ps_stdnt_enrl e
    WHERE
        e.acad_career='UGRD' AND
        e.stdnt_enrl_status='E' AND
        e.include_in_gpa='Y' AND
        e.crse_grade_off <> ' ' AND
        e.emplid in $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                ps_class_tbl c
            WHERE
                e.strm = c.strm AND
                e.class_nbr = c.class_nbr AND
                c.catalog_nbr >= ' 300' AND
                c.catalog_nbr <= ' 499' AND
                c.subject IN $subjects
        )
    GROUP BY emplid
        
    """)
    default_arguments = { 
        'emplids': ['301008183'], 
        'subjects':["CMPT"]
        }

class LDGPA_Query(DB2_Query):
    title = "Computed LDGPA Query"
    description = "Compute a list of student-to-LDGPA mappings. "

    query = string.Template("""
    SELECT DISTINCT
        emplid, 
        SUM( e.grade_points )/SUM( e.unt_taken ) as LDGPA
    FROM
        ps_stdnt_enrl e
    WHERE
        e.acad_career='UGRD' AND
        e.stdnt_enrl_status='E' AND
        e.include_in_gpa='Y' AND
        e.crse_grade_off <> ' ' AND
        e.emplid in $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                ps_class_tbl c
            WHERE
                e.strm = c.strm AND
                e.class_nbr = c.class_nbr AND
                c.catalog_nbr <= ' 299'
        )
    GROUP BY emplid
        
    """)
    default_arguments = { 'emplids': ['301008183'] }


