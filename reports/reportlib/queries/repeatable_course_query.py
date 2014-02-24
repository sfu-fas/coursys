from ..db2_query import DB2_Query
from ..semester import Semester, current_semester

import string

class RepeatableCourseQuery(DB2_Query):
    title = "Repeatable Course Query"
    description = "Fetch a list of courses that are repeatable." 
    query = string.Template("""
    SELECT DISTINCT 
        crse_id,
        crse_repeat_limit
    FROM 
        ps_crse_catalog
    WHERE 
        eff_status='A' 
        AND crse_repeatable='Y'
        """)
    default_arguments = { }


