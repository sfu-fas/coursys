from ..db2_query import DB2_Query
from ..semester import current_semester
import string

class CGPAQuery(DB2_Query):
    title = "Calculated GPA Query"
    description = "Fetch a complete list of pre-calculated student-to-GPA mappings by semester" 

    query = string.Template("""
    SELECT DISTINCT 
        EMPLID,
        CUM_GPA,
        TOT_PASSD_PRGRSS AS CREDITS
    FROM 
        PS_STDNT_CAR_TERM
    WHERE 
        STRM = $semester
        """)
    default_arguments = {
        'semester': current_semester()
        }

class GPA_Query(DB2_Query):
    title = "Computed GPA Query"
    description = "Compute a list of student-to-GPA mappings"

    query = string.Template("""
    SELECT DISTINCT
        EMPLID,
        SUM( E.GRADE_POINTS )/SUM( E.UNT_TAKEN ) AS CGPA
    FROM 
        PS_STDNT_ENRL E
    WHERE
        E.ACAD_CAREER='UGRD' AND
        E.STDNT_ENRL_STATUS='E' AND
        E.INCLUDE_IN_GPA='Y' AND
        E.CRSE_GRADE_OFF <> ' ' AND
        E.EMPLID IN $emplids
    GROUP BY EMPLID
    """)
    default_arguments = { 'emplids': ['301008183'] }

class UDGPA_Query(DB2_Query):
    title = "Computed UDGPA Query"
    description = "Compute a list of student-to-UDGPA mappings. "

    query = string.Template("""
    SELECT DISTINCT
        EMPLID,
        SUM( E.GRADE_POINTS )/SUM( E.UNT_TAKEN ) AS UDGPA
    FROM
        PS_STDNT_ENRL E
    WHERE
        E.ACAD_CAREER='UGRD' AND
        E.STDNT_ENRL_STATUS='E' AND
        E.INCLUDE_IN_GPA='Y' AND
        E.CRSE_GRADE_OFF <> ' ' AND
        E.EMPLID IN $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                PS_CLASS_TBL C
            WHERE
                E.STRM = C.STRM AND
                E.CLASS_NBR = C.CLASS_NBR AND
                C.CATALOG_NBR >= ' 300' AND
                C.CATALOG_NBR <= ' 499' 
        )
    GROUP BY EMPLID
        
    """)
    default_arguments = { 'emplids': ['301008183'] }

class Subject_UDGPA_Query(DB2_Query):
    title = "Subject UDGPA Query"
    description = "Compute a list of student-to-UDGPA mappings for courses in a specific subject. "

    query = string.Template("""
    SELECT DISTINCT
        EMPLID,
        SUM( E.GRADE_POINTS )/SUM( E.UNT_TAKEN ) AS SUBJECT_UDGPA
    FROM
        PS_STDNT_ENRL E
    WHERE
        E.ACAD_CAREER='UGRD' AND
        E.STDNT_ENRL_STATUS='E' AND
        E.INCLUDE_IN_GPA='Y' AND
        E.CRSE_GRADE_OFF <> ' ' AND
        E.EMPLID IN $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                PS_CLASS_TBL C
            WHERE
                E.STRM = C.STRM AND
                E.CLASS_NBR = C.CLASS_NBR AND
                C.CATALOG_NBR >= ' 300' AND
                C.CATALOG_NBR <= ' 499' AND
                C.SUBJECT IN $subjects
        )
    GROUP BY EMPLID
        
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
        EMPLID, 
        SUM( E.GRADE_POINTS )/SUM( E.UNT_TAKEN ) AS LDGPA
    FROM
        PS_STDNT_ENRL E
    WHERE
        E.ACAD_CAREER='UGRD' AND
        E.STDNT_ENRL_STATUS='E' AND
        E.INCLUDE_IN_GPA='Y' AND
        E.CRSE_GRADE_OFF <> ' ' AND
        E.EMPLID IN $emplids AND
        EXISTS ( 
            SELECT 
                * 
            FROM 
                PS_CLASS_TBL C
            WHERE
                E.STRM = C.STRM AND
                E.CLASS_NBR = C.CLASS_NBR AND
                C.CATALOG_NBR <= ' 299'
        )
    GROUP BY EMPLID
        
    """)
    default_arguments = { 'emplids': ['301008183'] }


