from ..db2_query import DB2_Query
from ..semester import Semester, current_semester

import string

class RepeatableCourseQuery(DB2_Query):
    title = "Repeatable Course Query"
    description = "Fetch a list of courses that are repeatable." 
    query = string.Template("""
    SELECT DISTINCT 
        CRSE_ID,
        CRSE_REPEAT_LIMIT
    FROM 
        PS_CRSE_CATALOG
    WHERE 
        EFF_STATUS='A' 
        AND CRSE_REPEATABLE='Y'
        """)
    default_arguments = { }


