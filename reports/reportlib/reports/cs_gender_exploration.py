from ..report import Report
from ..db2_query import DB2_Query
from ..semester import current_semester

import string

INTERNAL_TRANSFER_SLUG = 'apsc-draft-computing-science-internal-transfer-app'


class GenderGroup(DB2_Query):
    title = "Gender breakdown of given emplids"
    description = "Gender breakdown of given emplids"

    query = string.Template("""
        SELECT sex AS gender, count(sex) AS count_internal_transer_applicants
        FROM ps_personal_data
        WHERE emplid IN $emplids
        GROUP BY sex
        """)
    default_arguments = {
        'emplids': ['301008183'],
        }


class CourseWaitlistGendersShort(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT c.subject, c.catalog_nbr, p.sex AS gender, COUNT(*) AS count
                 FROM ps_stdnt_enrl e
                 JOIN ps_class_tbl c
                   ON e.class_nbr=c.class_nbr AND e.strm=c.strm
                 JOIN ps_personal_data p
                   ON e.emplid=p.emplid
                 AND c.class_type='E' AND e.stdnt_enrl_status='W'
                 AND e.strm=$strm AND c.SUBJECT=$subject
                 GROUP BY c.subject, c.catalog_nbr, p.sex
                 ORDER BY c.subject, c.catalog_nbr, p.sex;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class CourseWaitlistGendersFull(DB2_Query):
    title = "Gender breakdown of course waitlists"
    description = "Gender breakdown of course waitlists"

    query = string.Template("""
        SELECT c.subject, c.catalog_nbr, e.acad_prog, p.sex AS gender, COUNT(*) AS count
                 FROM ps_stdnt_enrl e
                 JOIN ps_class_tbl c
                   ON e.class_nbr=c.class_nbr AND e.strm=c.strm
                 JOIN ps_personal_data p
                   ON e.emplid=p.emplid
                 AND c.class_type='E' AND e.stdnt_enrl_status='W'
                 AND e.strm=$strm AND c.SUBJECT=$subject
                 GROUP BY c.subject, c.catalog_nbr, e.acad_prog, p.sex
                 ORDER BY c.subject, c.catalog_nbr, e.acad_prog, p.sex;
        """)
    default_arguments = {
        'strm': current_semester(),
        'subject': 'CMPT',
        }


class CSGenderExplorationReport(Report):
    title = "CS Gender Exploration"
    description = "What are the different gender breakdowns in CS?"

    def get_transfer_applicants(self):
        # find Persons who have completed the internal transfer form
        from onlineforms.models import Form, SheetSubmission
        try:
            form = Form.objects.get(slug=INTERNAL_TRANSFER_SLUG)
            subsheets = SheetSubmission.objects.filter(sheet__form=form, status='DONE',
                                                       sheet__is_initial=True).select_related('filler',
                                                                                              'filler__sfuFormFiller')
            fillers = {ss.filler.sfuFormFiller.emplid for ss in subsheets if ss.filler.sfuFormFiller}
        except Form.DoesNotExist:
            fillers = {'301008183'}

        # query for their gender
        query = GenderGroup(query_args={'emplids': list(fillers)})
        self.artifacts.append(query.result())

    def get_waitlists(self):
        query = CourseWaitlistGendersShort()
        self.artifacts.append(query.result())
        query = CourseWaitlistGendersFull()
        self.artifacts.append(query.result())

    def run(self):
        self.get_transfer_applicants()
        self.get_waitlists()


