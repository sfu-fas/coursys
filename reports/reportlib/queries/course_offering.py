from ..db2_query import DB2_Query
from ..semester import current_semester
import string

class CourseOfferingQuery(DB2_Query):
    title = "Course Offering Query"
    description = "Fetch a complete list of course offerings."

    query = string.Template("""
    SELECT DISTINCT
        STRM,
        SUBJECT,
        CATALOG_NBR,
        LOCATION,
        ENRL_CAP,
        SSR_COMPONENT,
        ENRL_TOT
    FROM
        PS_CLASS_TBL
    WHERE
        SUBJECT IN $subjects
        """)
    default_arguments = {
        'subjects': ['CMPT', 'ENSC', 'MATH', 'MACM', 'PHYS', 'STAT']
        }
