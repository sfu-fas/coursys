from ..db2_query import DB2_Query
from ..semester import current_semester
import string

class CourseOfferingQuery(DB2_Query):
    title = "Course Offering Query"
    description = "Fetch a complete list of course offerings."

    query = string.Template("""
    SELECT DISTINCT
        strm,
        subject,
        catalog_nbr,
        location,
        enrl_cap,
        ssr_component,
        enrl_tot
    FROM
        ps_class_tbl
    WHERE
        subject in $subjects
        """)
    default_arguments = {
        'subjects': ['CMPT', 'ENSC', 'MATH', 'MACM', 'PHYS', 'STAT']
        }
