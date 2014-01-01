import sys, os, datetime, time, copy
import MySQLdb
sys.path.append(".")
#sys.path.append("courses")
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'

from coredata.queries import SIMSConn, DBConn, get_names, grad_student_info, get_reqmnt_designtn, GRADFIELDS, REQMNT_DESIGNTN_FLAGS
from coredata.models import Person, Semester, SemesterWeek, Unit,CourseOffering, Member, MeetingTime, Role, ComputingAccount
from coredata.models import CAMPUSES, COMPONENTS, INSTR_MODE
from dashboard.models import NewsItem
from log.models import LogEntry
from django.db import transaction
from django.db.utils import IntegrityError
from django.contrib.sessions.models import Session
from django.conf import settings
from courselib.svn import update_offering_repositories
from grad.models import GradStudent, create_or_update_student, STATUS_ACTIVE, STATUS_APPLICANT
import itertools, random

today = datetime.date.today()
past_cutoff = today - datetime.timedelta(days=30)
future_cutoff = today + datetime.timedelta(days=90)

# these users will be given sysadmin role (for bootstrapping)
#sysadmin = ["ggbaker", "sumo"]
sysadmin = ["ggbaker"]

# artificial combined sections to create: kwargs for CourseOffering creation,
# plus 'subsections' list of sections we're combining.

def get_combined():
    
    # IMPORTANT: When combining sections in the future, ensure that the created
    #            section has 'owner': Unit(~CMPT~) 
    combined_sections = [
        {
            'subject': 'CMPT', 'number': '419', 'section': 'X100',
            'semester': Semester.objects.get(name="1137"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32759, 'class_nbr': 32759,
            'title': 'Biomedical Image Computing (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2013fa-cmpt-419-d1'),
                CourseOffering.objects.get(slug='2013fa-cmpt-829-g1')
            ]
        },
        {
            'subject': 'STAT', 'number': '340', 'section': 'X100',
            'semester': Semester.objects.get(name="1141"),
            'component': 'LEC', 'graded': True,
            'crse_id': 32752, 'class_nbr': 32752,
            'title': 'Stat Comp Data Ana (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2014sp-stat-340-d1'),
                CourseOffering.objects.get(slug='2014sp-stat-341-d1'),
                CourseOffering.objects.get(slug='2014sp-stat-342-d1'),
            ]
        },
        {
            'subject': 'STAT', 'number': '403', 'section': 'X100',
            'semester': Semester.objects.get(name="1141"),
            'component': 'LEC', 'graded': True,
            'crse_id': 32751, 'class_nbr': 32751,
            'title': 'Sampl./Exper. Des. (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2014sp-stat-403-d1'),
                CourseOffering.objects.get(slug='2014sp-stat-650-g1'),
                CourseOffering.objects.get(slug='2014sp-stat-890-g1'),
            ]
        },
#        {
#            'subject': 'CMPT', 'number': '419', 'section': 'X100',
#            'semester': Semester.objects.get(name="1127"),
#            'component': 'LEC', 'graded': True, 
#            'crse_id': 32754, 'class_nbr': 32754,
#            'title': 'Bioinformatics (combined sections)',
#            'campus': 'BRNBY',
#            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
#            'config': {},
#            'subsections': [
#                CourseOffering.objects.get(slug='2012fa-cmpt-419-e1'),
#                CourseOffering.objects.get(slug='2012fa-cmpt-829-g1')
#            ]
#        },
#        {
#            'subject': 'CMPT', 'number': '441', 'section': 'X100',
#            'semester': Semester.objects.get(name="1127"),
#            'component': 'LEC', 'graded': True, 
#            'crse_id': 32753, 'class_nbr': 32753,
#            'title': 'Computational Biology',
#            'campus': 'BRNBY',
#            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
#            'config': {},
#            'subsections': [
#                CourseOffering.objects.get(slug='2012fa-cmpt-441-d1'),
#                CourseOffering.objects.get(slug='2012fa-cmpt-711-g1')
#            ]
#        },
#        {
#            'subject': 'MACM', 'number': '101', 'section': 'X100',
#            'semester': Semester.objects.get(name="1131"),
#            'component': 'LEC', 'graded': True, 
#            'crse_id': 32755, 'class_nbr': 32755,
#            'title': 'Discrete Math I',
#            'campus': 'BRNBY',
#            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
#            'config': {},
#            'subsections': [
#                CourseOffering.objects.get(slug='2013sp-macm-101-d1'),
#                CourseOffering.objects.get(slug='2013sp-macm-101-d2')
#            ]
#        },
#        {
#            'subject': 'CMPT', 'number': '125', 'section': 'X100',
#            'semester': Semester.objects.get(name="1131"),
#            'component': 'LEC', 'graded': True, 
#            'crse_id': 32756, 'class_nbr': 32756,
#            'title': 'Intro.Cmpt.Sci/Programming II',
#            'campus': 'BRNBY',
#            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
#            'config': {},
#            'subsections': [
#                CourseOffering.objects.get(slug='2013sp-cmpt-125-d1'),
#                CourseOffering.objects.get(slug='2013sp-cmpt-126-d1')
#            ]
#        },
        {
            'subject': 'CMPT', 'number': '125', 'section': 'X100',
            'semester': Semester.objects.get(name="1134"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32757, 'class_nbr': 32757,
            'title': 'Intro.Cmpt.Sci/Programming II',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2013su-cmpt-125-d1'),
                CourseOffering.objects.get(slug='2013su-cmpt-126-d1')
            ]
        },
        {
            'subject': 'CMPT', 'number': '125', 'section': 'X100',
            'semester': Semester.objects.get(name="1137"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32758, 'class_nbr': 32758,
            'title': 'Intro.Cmpt.Sci/Programming II',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2013fa-cmpt-125-d1'),
                CourseOffering.objects.get(slug='2013fa-cmpt-126-d1')
            ]
        },
        ]
    return combined_sections

class MySQLConn(DBConn):
    db_host = '127.0.0.1'
    db_port = 4000
    def escape_arg(self, a):
        return "'" + MySQLdb.escape_string(str(a)) + "'"


class AMAINTConn(MySQLConn):
    """
    Singleton object representing AMAINT DB connection
    """
    db_user = "ggbaker"
    db_name = "amaint"

    def get_connection(self):
        passfile = open(self.dbpass_file)
        pw = passfile.next().strip()

        conn = MySQLdb.connect(host=self.db_host, user=self.db_user,
             passwd=pw, db=self.db_name, port=self.db_port)
        return conn, conn.cursor()

class TAConn(MySQLConn):
    """
    Singleton object representing TA DB connection
    """
    db_user = "ta_data_import"
    db_name = "ta_data_drop"

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        pw = passfile.next().strip()

        conn = MySQLdb.connect(host=self.db_host, user=self.db_user,
             passwd=pw, db=self.db_name, port=self.db_port)
        return conn, conn.cursor()


@transaction.atomic
def create_semesters():
    pass
    # should be done in the admin interface: https://courses.cs.sfu.ca/sysadmin/semesters/

@transaction.atomic
def fix_emplid():
    """
    Any manually-entered people will have emplid 0000?????.  Update them with the real emplid from the database.
    """
    people = Person.objects.filter(emplid__lt=100000)
    for p in people:
        #print " ", p.userid
        cas = ComputingAccount.objects.filter(userid=p.userid)
        for ca in cas:
            p.emplid = ca.emplid
            p.save()


def import_semester(sems):
    """
    Should this QuerySet of semesters be imported?
    """
    if not sems:
        return False
    s = sems[0]
    return s.end >= past_cutoff and s.start <= future_cutoff

def import_semesters():
    """
    What semesters should we actually import? (returns tuple of strm values)
    """
    sems = Semester.objects.filter(end__gte=past_cutoff, start__lte=future_cutoff)
    return tuple(s.name for s in sems)

def get_unit(acad_org):
    """
    Get the corresponding Unit
    """
    # in older semesters, there are some inconsistent acad_org values: normalize.
    if acad_org == 'GERON':
        acad_org = 'GERONTOL'
    elif acad_org == 'GEOG':
        acad_org = 'GEOGRAPH'
    elif acad_org == 'BUS':
        acad_org = 'BUS ADMIN'

    try:
        unit = Unit.objects.get(acad_org=acad_org)
    except Unit.DoesNotExist:
        db = SIMSConn()
        db.execute("SELECT descrformal FROM ps_acad_org_tbl "
                   "WHERE eff_status='A' and acad_org=%s", (acad_org,))
        
        name, = db.fetchone()
        if acad_org == 'ENVIRO SCI':
            label = 'ENVS'
        else:
            label = acad_org[:4].strip()
        #unit = Unit(acad_org=acad_org, label=label, name=name, parent=None)
        #unit.save()
        raise KeyError, "Unknown unit: acad_org=%s, label~=%s, name~=%s." % (acad_org, label, name)
    
    return unit
        
REQ_DES = None
@transaction.atomic
def import_offering(subject, number, section, strm, crse_id, class_nbr, component, title, campus,
                    enrl_cap, enrl_tot, wait_tot, cancel_dt, acad_org, instr_mode, rqmnt_designtn, units):
    """
    Import one offering. Returns CourseOffering or None.
    
    Arguments must be in the same order as CLASS_TBL_FIELDS.
    """
    global REQ_DES
    if not REQ_DES:
        REQ_DES = get_reqmnt_designtn()
    semester = Semester.objects.get(name=strm)
    graded = True # non-graded excluded in with "class_type='E'" in query

    # make sure the data is as we expect:
    if not CAMPUSES.has_key(campus):
        raise KeyError, "Unknown campus: %r." % (campus)
    if not COMPONENTS.has_key(component):
        raise KeyError, "Unknown course component: %r." % (component)
    if not INSTR_MODE.has_key(instr_mode):
        raise KeyError, "Unknown instructional mode: %r." % (instr_mode)

    if cancel_dt is not None:
        # mark cancelled sections
        component = "CAN"
    
    owner = get_unit(acad_org)

    # search for existing offerings both possible ways and make sure we're consistent
    c_old1 = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester).select_related('course')
    c_old2 = CourseOffering.objects.filter(class_nbr=class_nbr, semester=semester)
    c_old = list(set(c_old1) | set(c_old2))
    
    if len(c_old)>1:
        raise KeyError, "Already duplicate courses: %r" % (c_old1)
    elif len(c_old)==1:
        # already in DB: update things that might have changed
        c = c_old[0]
    else:
        # new record: create.
        c = CourseOffering(subject=subject, number=number, section=section, semester=semester)

    c.crse_id = crse_id
    c.class_nbr = class_nbr
    c.component = component
    c.graded = graded
    c.title = title
    c.campus = campus
    c.enrl_cap = enrl_cap
    c.enrl_tot = enrl_tot
    c.wait_tot = wait_tot
    c.owner = owner
    c.instr_mode = instr_mode
    c.units = units
    c.slug = c.autoslug() # rebuild slug in case section changes for some reason

    # set the WQB flags
    flags = REQMNT_DESIGNTN_FLAGS[REQ_DES.get(rqmnt_designtn, '')]
    for pos, key in enumerate(c.flags.keys()):
        c.flags.set_bit(pos, key in flags)

    c.save()
    
    crs = c.course
    if crs.title != c.title:
        crs.title = c.title
        crs.save()

    return c

CLASS_TBL_FIELDS = 'ct.subject, ct.catalog_nbr, ct.class_section, ct.strm, ct.crse_id, ct.class_nbr, ' \
        + 'ct.ssr_component, ct.descr, ct.campus, ct.enrl_cap, ct.enrl_tot, ct.wait_tot, ct.cancel_dt, ' \
        + 'ct.acad_org, ct.instruction_mode, cc.rqmnt_designtn, cc.units_minimum'
CLASS_TBL_QUERY = """
SELECT """ + CLASS_TBL_FIELDS + """
FROM ps_class_tbl ct
  LEFT OUTER JOIN ps_crse_catalog cc ON ct.crse_id=cc.crse_id
  LEFT OUTER JOIN ps_term_tbl t ON ct.strm=t.strm AND ct.acad_career=t.acad_career
WHERE
  cc.eff_status='A' AND ct.class_type='E'
  AND cc.effdt=(SELECT MAX(effdt) FROM ps_crse_catalog
                WHERE crse_id=cc.crse_id AND eff_status='A' AND effdt<=t.term_begin_dt)
""" # AND more stuff added where it is used.
# Note that this query can return multiple rows where one course was entered in multiple sessions
# (e.g. import_one_offering(strm='1014', subject='CMPT', number='310', section='D100')
# They seem to have different class_nbr values, but are otherwise identical.
# Students are imported by class_nbr but are unified in our DB, so that might be bad, but it hasn't come up.

def import_one_offering(strm, subject, number, section):
    """
    Find a single offering by its details (used by Cortez data importer).
    """
    db = SIMSConn()
    db.execute(CLASS_TBL_QUERY +
               "AND ct.strm=%s and ct.subject=%s and ct.catalog_nbr LIKE %s and ct.class_section=%s",
               (strm, subject, '%'+number+'%', section))

    # can have multiple results for intersession courses (and others?). Just taking the first.
    res = list(db)
    if not res:
        # lots of section numbers wrong in cortez: try finding any section as a fallback
        db.execute(CLASS_TBL_QUERY
               + "AND ct.strm=%s AND ct.subject=%s AND ct.catalog_nbr LIKE %s",
               (strm, subject, '%'+number+'%'))
        res = list(db)
        if res:
            row = res[0]
            return import_offering(*row)
        return None

    row = res[0]
    return import_offering(*row)
    
def import_offerings(extra_where='1=1', import_semesters=import_semesters, cancel_missing=False):
    db = SIMSConn()
    db.execute(CLASS_TBL_QUERY + " AND ct.strm IN %s "
               " AND ("+extra_where+")", (import_semesters(),))
    imported_offerings = set()
    for row in db.rows():
        o = import_offering(*row)
        if o:
            imported_offerings.add(o)

    if cancel_missing:
        # mark any offerings not found during the import as cancelled: handles sections that just disappear from
        # ps_class_tbl, because that can happen, apparently.
        all_off = CourseOffering.objects.filter(semester__name__in=import_semesters()) \
            .exclude(component='CAN').exclude(flags=CourseOffering.flags.combined)
        all_off = set(all_off)
        for o in all_off - imported_offerings:
            o.component = 'CAN'
            o.save()
    
    return imported_offerings


def _person_save(p):
    """
    Save this person object, dealing with duplicate userid as appropriate
    """
    try:
        p.save()
    except IntegrityError:
        print "    Changed userid: " + p.userid
        # other account with this userid must have been deactivated: update
        other = Person.objects.get(userid=p.userid)
        assert other.emplid != p.emplid
        get_person(other.emplid)
        # try again now
        p.save()

imported_people = {}
IMPORT_THRESHOLD = 3600*24*7 # import personal info only once a week
def get_person(emplid, commit=True, force=False):
    """
    Get/update personal info for this emplid and return (updated & saved) Person object.
    """
    global imported_people
    # use imported_people as a cache
    if emplid in imported_people:
        return imported_people[emplid]

    # either get old or create new Person object    
    p_old = Person.objects.filter(emplid=emplid)
    if len(p_old)>1:
        raise KeyError, "Already duplicate people: %r" % (p_old)
    elif len(p_old)==1:
        p = p_old[0]
    else:
        p = Person(emplid=emplid)
    imported_people[emplid] = p

    # only import if data is older than IMPORT_THRESHOLD (unless forced)
    # Randomly occasionally import anyway, so new students don't stay bunched-up.
    if random.random() < 0.95 and not force and 'lastimport' in p.config \
            and time.time() - p.config['lastimport'] < IMPORT_THRESHOLD:
        return p
    
    # get their names
    last_name, first_name, middle_name, pref_first_name, title = get_names(emplid)
    if last_name is None:
        # no name = no such person
        p.userid = None
        p.save()
        return p
    
    # get userid
    try:
        ca = ComputingAccount.objects.get(emplid=p.emplid)
        userid = ca.userid
    except ComputingAccount.DoesNotExist:
        userid = None
    
    if p.userid and p.userid != userid and userid is not None:
        raise ValueError, "Did somebody's userid change? " + `p.userid` + " " +  `userid`
    
    # update person's data
    if userid is not None:
        p.userid = userid
    p.last_name = last_name
    p.first_name = first_name
    p.middle_name = middle_name
    p.pref_first_name = pref_first_name
    p.title = title
    p.config['lastimport'] = int(time.time())
    if commit:
        _person_save(p)

    return p
    

imported_people_full = {}
def get_person_grad(emplid, commit=True, force=False):
    """
    Get/update personal info: does get_person() plus additional info we need for grad students
    """
    global imported_people_full
    # use imported_people_full as a cache
    if emplid in imported_people_full:
        return imported_people_full[emplid]
    
    p = get_person(emplid, commit=False)
    
    imported_people_full[emplid] = p

    # only import if data is older than IMPORT_THRESHOLD (unless forced)
    # Randomly occasionally import anyway, so new students don't stay bunched-up.
    if random.random() < 0.95 and not force and 'lastimportgrad' in p.config \
            and time.time() - p.config['lastimportgrad'] < IMPORT_THRESHOLD:
        return p
   
    create_or_update_student(emplid)
    data = grad_student_info(emplid)
    p.config.update(data)

    # if we tried to update but it's gone: don't keep old version
    for f in GRADFIELDS:
        if f not in data and f in p.config:
            del p.config[f]
    
    p.config['lastimportgrad'] = int(time.time())
    if commit:
        _person_save(p)
    
    return p


def fix_mtg_info(section, stnd_mtg_pat):
    """
    Normalize SIMS meeting data to something we can deal with.
    """
    # section: None for lecture/exams; lab/tutorial section for them.
    if section.endswith("00"):
        sec = None
    else:
        sec = section

    # meeting type: exams, lab/tutorials, other=lecture
    if stnd_mtg_pat in ['EXAM', 'MIDT']:
        mtype = stnd_mtg_pat
    elif not section.endswith('00'):
        mtype = 'LAB'
    else:
        mtype = 'LEC'
    
    return sec, mtype

@transaction.atomic
def import_meeting_times(offering):
    """
    Import course meeting times
    """
    db = SIMSConn()
    db.execute("SELECT meeting_time_start, meeting_time_end, facility_id, mon,tues,wed,thurs,fri,sat,sun, "
               "start_dt, end_dt, stnd_mtg_pat, class_section FROM ps_class_mtg_pat "
               "WHERE crse_id=%s and class_section like %s and strm=%s",
               ("%06i" % (int(offering.crse_id)), offering.section[0:2]+"%", offering.semester.name))
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()
    
    for start,end, room, mon,tues,wed,thurs,fri,sat,sun, start_dt,end_dt, stnd_mtg_pat, class_section in db:
        # dates come in as strings from DB2/reporting DB
        start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d").date()
        if not start or not end:
            # some meeting times exist with no start/end time
            continue        

        wkdays = [n for n, day in zip(range(7), (mon,tues,wed,thurs,fri,sat,sun)) if day=='Y']
        labtut_section, mtg_type = fix_mtg_info(class_section, stnd_mtg_pat)
        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=offering, weekday=wkd, start_time=start, end_time=end, labtut_section=labtut_section, room=room)
            if len(m_old)>1:
                raise KeyError, "Already duplicate meeting: %r" % (m_old)
            elif len(m_old)==1:
                # new data: just replace.
                m_old = m_old[0]
                if m_old.start_day==start_dt and m_old.end_day==end_dt and m_old.room==room \
                        and m_old.meeting_type==mtg_type and m_old.labtut_section==labtut_section:
                    # unchanged: leave it.
                    found_mtg.add(m_old.id)
                    continue
                else:
                    # it has changed: remove and replace.
                    m_old.delete()
            
            m = MeetingTime(offering=offering, weekday=wkd, start_day=start_dt, end_day=end_dt,
                            start_time=start, end_time=end, room=room, labtut_section=labtut_section)
            m.meeting_type = mtg_type
            m.save()
            found_mtg.add(m.id)
    
    # delete any meeting times we haven't found in the DB
    MeetingTime.objects.filter(offering=offering).exclude(id__in=found_mtg).delete()



def ensure_member(person, offering, role, cred, added_reason, career, labtut_section=None, grade=None):
    """
    Make sure this member exists with the right properties.
    """
    if person.emplid in [200133427, 200133425, 200133426]:
        # these are: ["Faculty", "Tba", "Sessional"]. Ignore them: they're ugly.
        return
    
    m_old = Member.objects.filter(person=person, offering=offering)

    if len(m_old)>1:
        # may be other manually-created dropped entries: that's okay.
        m_old = Member.objects.filter(person=person, offering=offering).exclude(role="DROP")
        if len(m_old)>1:
            raise KeyError, "Already duplicate entries: %r" % (m_old)
        elif len(m_old)==0:
            m_old = Member.objects.filter(person=person, offering=offering)
        
    if len(m_old)>=1:
        m = m_old[0]
    else:
        m = Member(person=person, offering=offering)

    m.role = role
    m.labtut_section = labtut_section
    m.credits = cred
    m.added_reason = added_reason
    m.career = career

    # record official grade if we have it
    m.official_grade = grade or None
    
    # if offering is being given lab/tutorial sections, flag it as having them
    # there must be some way to detect this in ps_class_tbl, but I can't see it.
    if labtut_section and not offering.labtut():
        offering.set_labtut(True)
        offering.save()
    
    m.save()
    return m

@transaction.atomic
def import_instructors(offering):
    "Import instructors for this offering"
    Member.objects.filter(added_reason="AUTO", offering=offering, role="INST").update(role='DROP')
    db = SIMSConn()
    db.execute("SELECT emplid, instr_role, sched_print_instr FROM ps_class_instr WHERE " \
               "crse_id=%s and class_section=%s and strm=%s and instr_role='PI' and sched_print_instr='Y'",
               ("%06i" % (int(offering.crse_id)), offering.section, offering.semester.name))
    for emplid, _, _ in db.rows():
        if not emplid:
            continue
        p = get_person(emplid)
        ensure_member(p, offering, "INST", 0, "AUTO", "NONS")

@transaction.atomic
def import_tas(offering):
    "Import TAs from cortez for this offering: no longer used since cortez is gone"
    if offering.subject not in ['CMPT', 'MACM']:
        return

    nbr = offering.number
    if nbr[-1] == "W":
        nbr = nbr[:-1]

    Member.objects.filter(added_reason="AUTO", offering=offering, role="TA").update(role='DROP')
    tadb = TAConn()
    tadb.execute("SELECT emplid, userid FROM ta_data WHERE strm=%s and subject=%s and " \
                 "catalog_nbr REGEXP %s and class_section=%s", \
                 (offering.semester.name, offering.subject, nbr+"W?", offering.section[0:2]))
    for emplid, userid in tadb:
        p = get_person(emplid)
        if p is None:
            print "    Unknown TA:", emplid, userid
            return
        ensure_member(p, offering, "TA", 0, "AUTO", "NONS")

@transaction.atomic
def import_students(offering):
    Member.objects.filter(added_reason="AUTO", offering=offering, role="STUD").update(role='DROP')
    db = SIMSConn()
    # find any lab/tutorial sections
    
    # c1 original lecture section
    # c2 related lab/tutorial section
    # s students in c2
    # WHERE lines: (1) match lab/tut sections of c1 class (2) students in those
    # lab/tut sections (3) with c1 matching offering
    query = "SELECT s.emplid, c2.class_section " \
        "FROM ps_class_tbl c1, ps_class_tbl c2, ps_stdnt_enrl s " \
        "WHERE c1.subject=c2.subject and c1.catalog_nbr=c2.catalog_nbr and c2.strm=c1.strm " \
        "and s.class_nbr=c2.class_nbr and s.strm=c2.strm and s.enrl_status_reason IN ('ENRL','EWAT') " \
        "and c1.class_nbr=%s and c1.strm=%s and c2.class_section LIKE %s"
    db.execute(query, (offering.class_nbr, offering.semester.name, offering.section[0:2]+"%"))
    labtut = {}
    for emplid, section in db:
        if section == offering.section:
            # not interested in lecture section now.
            continue
        labtut[emplid] = section
    
    db.execute("SELECT e.emplid, e.acad_career, e.unt_taken, e.crse_grade_off, r.crse_grade_input "
               "FROM ps_stdnt_enrl e LEFT JOIN ps_grade_roster r "
               "ON e.strm=r.strm and e.acad_career=r.acad_career and e.emplid=r.emplid and e.class_nbr=r.class_nbr "
               "WHERE e.class_nbr=%s and e.strm=%s and e.stdnt_enrl_status='E'", (offering.class_nbr, offering.semester.name))
    for emplid, acad_career, unt_taken, grade_official, grade_roster in db.rows():
        p = get_person(emplid)
        sec = labtut.get(emplid, None)
        grade = grade_official or grade_roster
        ensure_member(p, offering, "STUD", unt_taken, "AUTO", acad_career, labtut_section=sec, grade=grade)            

def import_offering_members(offering, students=True):
    """
    Import all data for the course: instructors, TAs, students, meeting times.
    
    students=False used by test/demo importers
    """
    import_instructors(offering)
    if students:
        #import_tas(offering)
        import_students(offering)
    import_meeting_times(offering)
    if settings.SVN_DB_CONNECT:
        update_offering_repositories(offering)


@transaction.atomic
def import_combined(extra_where='1=1'):
    """
    Find combined sections and set CourseOffering.config['combined_with'] appropriately.
    """
    db = SIMSConn()
    db.execute("SELECT strm, class_nbr, sctn_combined_id FROM ps_sctn_cmbnd c WHERE c.strm IN %s "
               " AND ("+extra_where+")", (import_semesters(),))

    for k,v in itertools.groupby(db, lambda d: (d[0], d[2])):
        # for each combined offering...
        strm, _ = k
        class_nbrs = [int(class_nbr) for _,class_nbr,_ in v]
        offerings = CourseOffering.objects.filter(semester__name=strm, class_nbr__in=class_nbrs)
        for offering in offerings:
            offering.set_combined_with([o.slug for o in offerings if o != offering])
            offering.save()


@transaction.atomic
def combine_sections(combined):
    """
    Combine sections in the database to co-offered courses look the same.
    """
    for info in combined:
        # create the section if necessary
        courses = CourseOffering.objects.filter(subject=info['subject'], number=info['number'], section=info['section'], semester=info['semester'], component=info['component'], campus=info['campus'])
        if courses:
            course = courses[0]
        else:
            kwargs = copy.copy(info)
            del kwargs['subsections']
            course = CourseOffering(**kwargs)
            course.save()

        print "  ", course        
        cap_total = 0
        tot_total = 0
        wait_total = 0
        labtut = False
        in_section = set() # students who are in section and not dropped (so we don't overwrite with a dropped membership)
        for sub in info['subsections']:
            cap_total += sub.enrl_cap
            tot_total += sub.enrl_tot
            wait_total += sub.wait_tot
            labtut = labtut or sub.labtut()
            for m in sub.member_set.all():
                old_ms = course.member_set.filter(offering=course, person=m.person)
                if old_ms:
                    # was already a member: update.
                    old_m = old_ms[0]
                    old_m.role = m.role
                    old_m.credits = m.credits
                    old_m.career = m.career
                    old_m.added_reason = m.added_reason
                    old_m.config['origsection'] = sub.slug
                    old_m.labtut_section = m.labtut_section
                    if m.role != 'DROP' or old_m.person_id not in in_section:
                        # condition keeps from overwriting enrolled students with drops (from other section)
                        old_m.save()
                    if m.role != 'DROP':
                        in_section.add(old_m.person_id)
                else:
                    # new membership: duplicate into combined
                    new_m = Member(offering=course, person=m.person, role=m.role, labtut_section=m.labtut_section,
                            credits=m.credits, career=m.career, added_reason=m.added_reason)
                    new_m.config['origsection'] = sub.slug
                    new_m.save()
                    if m.role != 'DROP':
                        in_section.add(new_m.person_id)

        # update totals        
        course.enrl_cap = cap_total
        course.tot_total = tot_total
        course.wait_total = wait_total
        course.set_labtut(labtut)
        course.set_combined(True)
        course.save()


@transaction.atomic
def give_sysadmin(sysadmin):
    """
    Give specified users sysadmin role (for bootstrapping)
    """
    for userid in sysadmin:
        p = Person.objects.get(userid=userid)
        r = Role.objects.filter(person=p, role="SYSA")
        if not r:
            r = Role(person=p, role="SYSA", unit=Unit.objects.get(label="UNIV"))
            r.save()

@transaction.atomic
def update_amaint_userids():
    """
    Refresh the AMAINT translation table
    """
    db = AMAINTConn()
    ComputingAccount.objects.all().delete()
    db.execute("SELECT username, emplid FROM idMap WHERE emplid!='' ORDER BY username", ())
    for userid, emplid in db:
        if emplid.startswith('E'):
            continue
        a = ComputingAccount(emplid=emplid, userid=userid)
        a.save()


@transaction.atomic
def update_all_userids():
    """
    Make sure everybody's userid is right.
    """
    db = AMAINTConn()
    accounts_by_emplid = dict((ca.emplid, ca) for ca in ComputingAccount.objects.all())
    
    for p in Person.objects.all():
        if p.emplid in accounts_by_emplid:
            account_userid = accounts_by_emplid[p.emplid].userid
            if p.userid != account_userid:
                p.userid = account_userid
                if account_userid:
                    p.config['replaced_userid'] = account_userid
                p.save()

        else:
            if p.userid:
                p.config['old_userid'] = p.userid
                p.userid = None
                p.save()


def update_grads():
    """
    Update any currently-relevant grad students
    """
    active = GradStudent.objects.filter(current_status__in=STATUS_ACTIVE).select_related('person')
    applicants = GradStudent.objects.filter(current_status__in=STATUS_APPLICANT,
                 updated_at__gt=datetime.datetime.now()-datetime.timedelta(days=7)).select_related('person')
    for gs in itertools.chain(active, applicants):
        get_person_grad(gs.person.emplid)


def import_one_semester(strm, extra_where='1=1'):
    """
    can be called manually to update non-student data for a single semester
    """
    sems = lambda: (strm,)
    offerings = import_offerings(extra_where=extra_where, import_semesters=sems)
    offerings = list(offerings)
    offerings.sort()
    for o in offerings:
        print o
        import_offering_members(o, students=False)


def main():
    global sysadmin

    print "getting emplid/userid mapping"
    update_amaint_userids()

    print "fixing any unknown emplids"
    fix_emplid()
    
    print "updating userids"
    update_all_userids()
    
    print "updating active grad students"
    update_grads()
    
    print "importing course offering list"
    #offerings = import_offerings(extra_where="subject IN ('GEOG', 'EDUC') and strm='1124' and catalog_nbr LIKE '%%9%%'")
    #offerings = import_offerings(extra_where="ct.subject='CMPT' and ct.catalog_nbr IN (' 470')")
    #offerings = import_offerings(extra_where="ct.subject='CMPT'")
    offerings = import_offerings(cancel_missing=True)
    offerings = list(offerings)
    offerings.sort()

    print "importing course members"
    last = None
    for o in offerings:
        if last != o.subject:
            print o.subject, o.semester
            last = o.subject
        import_offering_members(o)
        time.sleep(0.5)

    print "combining joint offerings"
    import_combined()
    combine_sections(get_combined())

    print "giving sysadmin permissions"
    give_sysadmin(sysadmin)
    
    # cleanup sessions table
    Session.objects.filter(expire_date__lt=datetime.datetime.now()).delete()
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=120)).delete()
    # cleanup old log entries
    LogEntry.objects.filter(datetime__lt=datetime.datetime.now()-datetime.timedelta(days=240)).delete()
    # cleanup already-run Celery jobs
    if settings.USE_CELERY:
        import djkombu.models
        djkombu.models.Message.objects.cleanup()
        from djcelery.models import TaskMeta
        TaskMeta.objects.filter(date_done__lt=datetime.datetime.now()-datetime.timedelta(days=120)).delete()
    
    print "People:", len(imported_people)
    print "Course Offerings:", len(offerings)


if __name__ == "__main__":
    main()

