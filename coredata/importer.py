import sys, os, datetime, time, copy
import MySQLdb
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from coredata.queries import SIMSConn, DBConn, get_names, grad_student_info, GRADFIELDS
from coredata.models import Person, Semester, SemesterWeek, Unit,CourseOffering, Member, MeetingTime, Role, ComputingAccount
from coredata.models import CAMPUSES, COMPONENTS
from dashboard.models import NewsItem
from log.models import LogEntry
from django.db import transaction
from django.db.utils import IntegrityError
from django.contrib.sessions.models import Session
from django.conf import settings
from courselib.svn import update_offering_repositories
today = datetime.date.today()
past_cutoff = today - datetime.timedelta(days=30)
future_cutoff = today + datetime.timedelta(days=60)

# these users will be given sysadmin role (for bootstrapping)
#sysadmin = ["ggbaker", "sumo"]
sysadmin = ["ggbaker"]

# artificial combined sections to create: kwargs for CourseOffering creation,
# plus 'subsections' list of sections we're combining.

def get_combined():
    combined_sections = [
        #{
        #    'subject': 'CMPT', 'number': '125', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1114"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32760, 'class_nbr': 32760,
        #    'title': 'Intro CS/Progr(combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='1114-cmpt-125-d100'),
        #        CourseOffering.objects.get(slug='1114-cmpt-126-d100')
        #    ]
        #},
        #{
        #    'subject': 'ENSC', 'number': '100', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1117"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32761, 'class_nbr': 32761,
        #    'title': 'Eng.Technology and Society (combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2011fa-ensc-100-d1'),
        #        CourseOffering.objects.get(slug='2011fa-ensc-100w-d1')
        #    ]
        #},
        #{
        #    'subject': 'CMPT', 'number': '120', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1117"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32762, 'class_nbr': 32762,
        #    'title': 'Intro.Cmpt.Sci/Programming I',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2011fa-cmpt-120-d1'),
        #        CourseOffering.objects.get(slug='2011fa-cmpt-120-d2')
        #    ]
        #},
        #{
        #    'subject': 'CMPT', 'number': '461', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1117"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32759, 'class_nbr': 32759,
        #    'title': 'Image Synthesis (ugrad/grad combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2011fa-cmpt-461-d1'),
        #        CourseOffering.objects.get(slug='2011fa-cmpt-761-g1')
        #    ]
        #},
        #{
        #    'subject': 'CMPT', 'number': '441', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1117"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32758, 'class_nbr': 32758,
        #    'title': 'Bioinformatics Alg (ugrad/grad combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2011fa-cmpt-441-e1'),
        #        CourseOffering.objects.get(slug='2011fa-cmpt-711-g1')
        #    ]
        #},
        #{
        #    'subject': 'CMPT', 'number': '165', 'section': 'C000',
        #    'semester': Semester.objects.get(name="1121"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32757, 'class_nbr': 32757,
        #    'title': 'Intro Internet/WWW (combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2012sp-cmpt-165-c1'),
        #        CourseOffering.objects.get(slug='2012sp-cmpt-165-c2'),
        #        CourseOffering.objects.get(slug='2012sp-cmpt-165-c3')
        #    ]
        #},
        #{
        #    'subject': 'MACM', 'number': '101', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1121"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32756, 'class_nbr': 32756,
        #    'title': 'Discrete Math I (combined)',
        #    'campus': 'BRNBY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2012sp-macm-101-d1'),
        #        CourseOffering.objects.get(slug='2012sp-macm-101-d2')
        #    ]
        #},
        #{
        #    'subject': 'CMPT', 'number': '471', 'section': 'X100',
        #    'semester': Semester.objects.get(name="1121"),
        #    'component': 'LEC', 'graded': True, 
        #    'crse_id': 32755, 'class_nbr': 32755,
        #    'title': 'Networking (ugrad/grad combined)',
        #    'campus': 'SURYY',
        #    'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
        #    'config': {},
        #    'subsections': [
        #        CourseOffering.objects.get(slug='2012sp-cmpt-471-d1'),
        #        CourseOffering.objects.get(slug='2012sp-cmpt-771-g1')
        #    ]
        #},
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


@transaction.commit_on_success
def create_semesters():
    # http://students.sfu.ca/calendar/for_students/dates.html
    s = Semester.objects.filter(name="1114")
    if not s:
        s = Semester(name="1114", start=datetime.date(2011, 5, 9), end=datetime.date(2011, 8, 8))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2011, 5, 9))
        wk.save()

    s = Semester.objects.filter(name="1117")
    if not s:
        s = Semester(name="1117", start=datetime.date(2011, 9, 6), end=datetime.date(2011, 12, 5))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2011, 9, 5))
        wk.save()

    s = Semester.objects.filter(name="1121")
    if not s:
        s = Semester(name="1121", start=datetime.date(2012, 1, 5), end=datetime.date(2012, 4, 11))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 1, 9))
        wk.save()
        wk = SemesterWeek(semester=s, week=6, monday=datetime.date(2012, 2, 20))
        wk.save()

    s = Semester.objects.filter(name="1124")
    if not s:
        s = Semester(name="1124", start=datetime.date(2012, 5, 7), end=datetime.date(2012, 8, 3))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 5, 7))
        wk.save()

    s = Semester.objects.filter(name="1127")
    if not s:
        s = Semester(name="1127", start=datetime.date(2012, 9, 4), end=datetime.date(2012, 12, 3))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 9, 3))
        wk.save()

    s = Semester.objects.filter(name="1131")
    if not s:
        s = Semester(name="1131", start=datetime.date(2013, 1, 7), end=datetime.date(2013, 4, 12))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2013, 1, 7))
        wk.save()
        wk = SemesterWeek(semester=s, week=7, monday=datetime.date(2013, 2, 25))
        wk.save()

    s = Semester.objects.filter(name="1134")
    if not s:
        s = Semester(name="1134", start=datetime.date(2013, 5, 6), end=datetime.date(2013, 8, 2))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2013, 5, 6))
        wk.save()



@transaction.commit_on_success
def fix_emplid():
    """
    Any manually-entered people will have emplid 0000?????.  Update them with the real emplid from the database.
    """
    amaint = AMAINTConn()
    people = Person.objects.filter(emplid__lt=100000)
    for p in people:
        print " ", p.userid
        amaint.execute('SELECT emplid FROM idMap WHERE username=%s', (p.userid,))
        for emplid, in amaint:
            p.emplid = emplid
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
    Get the corresponding Unit, importing if necessary
    """
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
        unit = Unit(acad_org=acad_org, label=label, name=name, parent=None)
        unit.save()
    
    return unit
        

@transaction.commit_on_success
def import_offering(subject, number, section, strm, crse_id, class_nbr, component, title, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt, acad_org):
    """
    Import one offering. Returns CourseOffering or None.
    
    Arguments must be in the same order as CLASS_TBL_FIELDS.
    """
    semester = Semester.objects.get(name=strm)
    graded = True # non-graded excluded in with "class_section like '%00'" in query

    # make sure the data is as we expect:
    if not CAMPUSES.has_key(campus):
        raise KeyError, "Unknown campus: %r." % (campus)
    if not COMPONENTS.has_key(component):
        raise KeyError, "Unknown course component: %r." % (component)

    if cancel_dt is not None:
        # mark cancelled sections
        component="CAN"
    
    owner = get_unit(acad_org)

    # search for existing offerings both possible ways and make sure we're consistent
    c_old1 = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester)
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
    c.slug = c.autoslug() # rebuild slug in case section changes for some reason
    c.save()
    
    crs = c.course
    if crs.title != c.title:
        crs.title = c.title
        crs.save()

    return c

CLASS_TBL_FIELDS = 'subject, catalog_nbr, class_section, strm, crse_id, class_nbr, ssr_component, descr, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt, acad_org' 

def import_one_offering(strm, subject, number, section):
    """
    Find a single offering by its details (used by Cortez data importer).
    """
    db = SIMSConn(verbose=False)
    db.execute("SELECT "+CLASS_TBL_FIELDS+" FROM ps_class_tbl WHERE "
               "strm=%s and subject=%s and catalog_nbr LIKE %s and class_section=%s",
               (strm, subject, '%'+number+'%', section))

    # can have multiple results for intersession courses (and others?). Just taking the first.
    res = list(db)
    if not res:
        # lots of section numbers wrong in cortez: try finding any section as a fallback
        db.execute("SELECT "+CLASS_TBL_FIELDS+" FROM ps_class_tbl WHERE "
               "strm=%s and subject=%s and catalog_nbr LIKE %s",
               (strm, subject, '%'+number+'%'))
        res = list(db)
        if res:
            row = res[0]
            return import_offering(*row)
        return None

    row = res[0]
    return import_offering(*row)
    
def import_offerings(extra_where='1=1', import_semesters=import_semesters):
    db = SIMSConn()
    db.execute("SELECT "+CLASS_TBL_FIELDS+" FROM ps_class_tbl WHERE strm IN %s AND "
               "class_section like '%%00' AND ("+extra_where+")", (import_semesters(),))
    imported_offerings = set()
    for row in db.rows():
        o = import_offering(*row)
        if o:
            imported_offerings.add(o)
    
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
def get_person(emplid, commit=True):
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
    
    # get their names
    last_name, first_name, middle_name, pref_first_name, title = get_names(emplid)
    if last_name is None:
        # no name = no such person
        p.userid = None
        p.save()
        return p
    
    # get userid from AMAINT
    amaintdb = AMAINTConn()
    amaintdb.execute('SELECT username FROM amaint.idMap WHERE emplid=%s', (emplid,))
    try:
        userid = amaintdb.fetchone()[0]
    except TypeError:
        userid = None
    
    if p.userid and p.userid != userid and userid is not None:
        raise ValueError, "Did somebody's userid change? " + `p.userid` + " " +  `userid`
    
    # update person's data
    p.userid = userid
    p.last_name = last_name
    p.first_name = first_name
    p.middle_name = middle_name
    p.pref_first_name = pref_first_name
    p.title = title
    if commit:
        _person_save(p)

    imported_people[emplid] = p
    return p
    

imported_people_full = {}
def get_person_grad(emplid, commit=True):
    """
    Get/update personal info: does get_person() plus additional info we need for grad students
    """
    global imported_people_full
    # use imported_people_full as a cache
    if emplid in imported_people_full:
        return imported_people_full[emplid]
    
    p = get_person(emplid, commit=False)
    
    data = grad_student_info(emplid)
    p.config.update(data)

    # if we tried to update but it's gone: don't keep old version
    for f in GRADFIELDS:
        if f not in data and f in p.config:
            del p.config[f]
    
    if commit:
        _person_save(p)
    imported_people_full[emplid] = p
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

@transaction.commit_on_success
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
    m_old = Member.objects.filter(person=person, offering=offering)

    if len(m_old)>1:
        # may be other manually-created dropped entries: that's okay.
        m_old = Member.objects.filter(person=person, offering=offering).exclude(role="DROP")
        if len(m_old)>1:
            raise KeyError, "Already duplicate entries: %r" % (m_old)
        m = m_old[0]
    if len(m_old)==1:
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

@transaction.commit_on_success
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

@transaction.commit_on_success
def import_tas(offering):
    "Import TAs from cortez for this offering"
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

@transaction.commit_on_success
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
        import_tas(offering)
        import_students(offering)
    import_meeting_times(offering)
    if settings.SVN_DB_CONNECT:
        update_offering_repositories(offering)


@transaction.commit_on_success
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


@transaction.commit_on_success
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

@transaction.commit_on_success
def update_amaint_userids():
    """
    Refresh the AMAINT translation table
    """
    db = AMAINTConn()
    ComputingAccount.objects.all().delete()
    db.execute("SELECT username, emplid FROM idMap WHERE emplid!='' ORDER BY username", ())
    for userid, emplid in db:
        a = ComputingAccount(emplid=emplid, userid=userid)
        a.save()




def main():
    global sysadmin

    create_semesters()

    print "fixing any unknown emplids"
    fix_emplid()
    
    print "importing course offering list"
    #offerings = import_offerings(extra_where="subject IN ('GEOG', 'EDUC') and strm='1124' and catalog_nbr LIKE '%%9%%'")
    #offerings = import_offerings(extra_where="subject='CMPT' and catalog_nbr IN (' 470')")
    #offerings = import_offerings(extra_where="subject='CMPT'")
    offerings = import_offerings()
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
    combine_sections(get_combined())

    print "getting emplid/userid mapping"
    update_amaint_userids()

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
    
    print "People:", len(imported_people)
    print "Course Offerings:", len(offerings)


if __name__ == "__main__":
    main()

