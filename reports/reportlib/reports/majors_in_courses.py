from reports.reportlib.report import Report
from ..db2_query import DB2_Query, Unescaped
import string, datetime

class PlansAsOfQuery(DB2_Query):
    title = "Students' program plans"
    description = "Students' program plans as of a particular date"

    query = string.Template("""
    SELECT emplid, stdnt_car_nbr, acad_plan
    FROM CS.PS_ACAD_PLAN A
    WHERE
       effdt=(SELECT MAX(effdt) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid AND effdt<=$date)
       AND effseq=(SELECT MAX(effseq) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid AND effdt=A.effdt)
       AND emplid IN $emplids
       ORDER BY emplid, plan_sequence""")

    def __init__(self, query_args):
        query_args['date'] = unicode(query_args['date'])
        super(PlansAsOfQuery, self).__init__(query_args)

    def result(self):
        return super(PlansAsOfQuery, self).result().flatten("EMPLID")



class CourseMembersQuery(DB2_Query):
    title = "Students in a course"
    description = "Get list of students in a course offering (emplids only)"

    query = string.Template("""
    SELECT s.emplid FROM ps_stdnt_enrl s
        WHERE s.class_nbr=$class_nbr and s.strm=$strm and s.enrl_status_reason IN ('ENRL','EWAT')""")

class CoursesInSemesterQuery(DB2_Query):
    title = "All course offerings in a semester"
    description = "Get list of all courses offered in a semester"

    query = string.Template("""
    SELECT subject, catalog_nbr, class_section, class_nbr, campus, trm.term_begin_dt
    FROM ps_class_tbl cls, ps_term_tbl trm
    WHERE
               cls.strm=trm.strm AND class_section LIKE '%%00' AND trm.acad_career='UGRD'
               AND cls.cancel_dt IS NULL AND cls.acad_org='COMP SCI'
               AND cls.strm=$strm
               ORDER BY subject ASC, catalog_nbr ASC, class_section ASC""")



class MajorsInCoursesReport(Report):
    title = "Majors in courses"
    description = "This report summarizes the academic programs of students in each FAS course."

    def run(self):
        strm = '1141'
        offerings = CoursesInSemesterQuery({'strm': strm}).result()
        self.artifacts.append(offerings)
        term_begin = offerings.column_as_list('TERM_BEGIN_DT')[0]
        for row in offerings.row_maps():
            class_nbr = row['CLASS_NBR']
            students_query = CourseMembersQuery({'class_nbr': unicode(class_nbr), 'strm': '1141'})
            students = students_query.result()
            emplids = students.column_as_list('EMPLID')
            emplids.sort()
            if not emplids:
                continue

            plans_query = PlansAsOfQuery({'date': term_begin, 'emplids': emplids})
            plans = plans_query.result()

            students.inner_join(plans, 'EMPLID')
            self.artifacts.append(students)




