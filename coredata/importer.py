import sys, os, datetime, time
sys.path.append(".")
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'

from coredata.queries import SIMSConn, get_reqmnt_designtn, import_person,\
    userid_to_emplid, cache_by_args, REQMNT_DESIGNTN_FLAGS
from coredata.models import Person, Semester, SemesterWeek, Unit,CourseOffering, Member, MeetingTime, Role, Holiday
from coredata.models import CombinedOffering, EnrolmentHistory, CAMPUSES, COMPONENTS, INSTR_MODE
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.core.mail import mail_admins
from courselib.svn import update_offering_repositories
from grades.models import LetterActivity
from grad.models import GradStudent, STATUS_ACTIVE, STATUS_APPLICANT, STATUS_GPA
from ra.models import RAAppointment
import itertools, random

today = datetime.date.today()
past_cutoff = today - datetime.timedelta(days=30)
future_cutoff = today + datetime.timedelta(days=150)


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
        if not p.userid:
            continue
        emplid = userid_to_emplid(p.userid)
        if emplid:
            p.emplid = emplid
            p.save_if_dirty()


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


def get_unit(acad_org, create=False):
    """
    Get the corresponding Unit
    """
    # there are some inconsistent acad_org values: normalize.
    if acad_org == 'GERON':
        acad_org = 'GERONTOL'
    elif acad_org == 'GEOG':
        acad_org = 'GEOGRAPH'
    elif acad_org == 'BUS':
        acad_org = 'BUS ADMIN'
    elif acad_org == 'HUM':
        acad_org = 'HUMANITIES'
    elif acad_org == 'EVSC':
        acad_org = 'ENVIRO SCI'

    try:
        unit = Unit.objects.get(acad_org=acad_org)
    except Unit.DoesNotExist:
        db = SIMSConn()
        db.execute("SELECT DESCRFORMAL FROM PS_ACAD_ORG_TBL "
                   "WHERE EFF_STATUS='A' AND ACAD_ORG=%s", (acad_org,))
        
        name, = db.fetchone()
        if acad_org == 'COMP SCI': # for test/demo imports
            label = 'CMPT'
        elif acad_org == 'ENG SCI': # for test/demo imports
            label = 'ENSC'
        elif acad_org == 'ENVIRONMEN': # for test/demo imports
            label = 'FENV'
        elif acad_org == 'DEAN GRAD': # for test/demo imports
            label = 'GRAD'
        else:
            label = acad_org[:4].strip()

        if create:
            unit = Unit(acad_org=acad_org, label=label, name=name, parent=None)
            unit.save()
        else:
            raise KeyError("Unknown unit: acad_org=%s, label~=%s, name~=%s." % (acad_org, label, name))

    return unit


REQ_DES = None
@transaction.atomic
def import_offering(subject, number, section, strm, crse_id, class_nbr, component, title, campus,
                    enrl_cap, enrl_tot, wait_tot, cancel_dt, acad_org, instr_mode, rqmnt_designtn, units,
                    create_units=False):
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
    if campus not in CAMPUSES:
        raise KeyError("Unknown campus: %r." % (campus))
    if component not in COMPONENTS:
        raise KeyError("Unknown course component: %r." % (component))
    if instr_mode not in INSTR_MODE:
        raise KeyError("Unknown instructional mode: %r." % (instr_mode))

    if cancel_dt is not None:
        # mark cancelled sections
        component = "CAN"

    if section == 'G':
        section = 'G100' # fix broken data somebody entered
    if section == 'R':
        section = 'G100' # fix different broken data somebody entered
    if section == '1':
        section = 'D100' # and another one

    owner = get_unit(acad_org, create=create_units)

    # search for existing offerings both possible ways and make sure we're consistent
    c_old1 = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester).select_related('course')
    c_old2 = CourseOffering.objects.filter(class_nbr=class_nbr, semester=semester)
    c_old = list(set(c_old1) | set(c_old2))
    
    if len(c_old)>1:
        #raise KeyError("Already duplicate courses: %r %r" % (c_old1, c_old2))
        c1 = c_old[0]
        c2 = c_old[1]
        with transaction.atomic():
            # somebody re-used a class_nbr: swap the .class_nbr for the two sections
            c1_nbr = c1.class_nbr
            c2_nbr = c2.class_nbr
            c1.class_nbr = 999999
            c1.save()
            c2.class_nbr = c1_nbr
            c2.save()
            c1.class_nbr = c2_nbr
            c1.save()
        mail_admins('class_nbr re-use', 'Conflict between class numbers on %s and %s: swapped their .class_nbr fields and carried on.' % (c1, c2))
        c = c_old1[0]
    elif len(c_old)==1:
        # already in DB: update things that might have changed
        c = c_old[0]
    else:
        # new record: create.
        c = CourseOffering(subject=subject, number=number, section=section, semester=semester)

    c.section = section
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

    c.save_if_dirty()
    
    crs = c.course
    if crs.title != c.title:
        crs.title = c.title
        crs.save()

    EnrolmentHistory.from_offering(c, save=True)

    return c


CLASS_TBL_FIELDS = 'CT.SUBJECT, CT.CATALOG_NBR, CT.CLASS_SECTION, CT.STRM, CT.CRSE_ID, CT.CLASS_NBR, ' \
        + 'CT.SSR_COMPONENT, CT.DESCR, CT.CAMPUS, CT.ENRL_CAP, CT.ENRL_TOT, CT.WAIT_TOT, CT.CANCEL_DT, ' \
        + 'CT.ACAD_ORG, CT.INSTRUCTION_MODE, CC.RQMNT_DESIGNTN, CC.UNITS_MINIMUM'
CLASS_TBL_QUERY = """
SELECT """ + CLASS_TBL_FIELDS + """
FROM PS_CLASS_TBL CT
  LEFT OUTER JOIN PS_CRSE_CATALOG CC ON CT.CRSE_ID=CC.CRSE_ID
  LEFT OUTER JOIN PS_TERM_TBL T ON CT.STRM=T.STRM AND CT.ACAD_CAREER=T.ACAD_CAREER
WHERE
  CC.EFF_STATUS='A' AND CT.CLASS_TYPE='E' AND CT.CLASS_STAT IN ('A','S')
  AND CC.EFFDT=(SELECT MAX(EFFDT) FROM PS_CRSE_CATALOG
                WHERE CRSE_ID=CC.CRSE_ID AND EFF_STATUS='A' AND EFFDT<=T.TERM_BEGIN_DT)
""" # AND more stuff added where it is used.
# Note that this query can return multiple rows where one course was entered in multiple sessions
# (e.g. import_one_offering(strm='1014', subject='CMPT', number='310', section='D100')
# They seem to have different class_nbr values, but are otherwise identical.
# Students are imported by class_nbr but are unified in our DB, so that might be bad, but it hasn't come up.
# CLASS_STAT values: 'A' = active; 'S' = stop further enrollment; 'T' = tentative section; 'X' = cancelled

def import_offerings(extra_where='1=1', import_semesters=import_semesters, cancel_missing=False, create_units=False):
    db = SIMSConn()
    db.execute(CLASS_TBL_QUERY + " AND CT.STRM IN %s "
               " AND ("+extra_where+")", (import_semesters(),))
    imported_offerings = set()
    for row in db.rows():
        o = import_offering(*row, create_units=create_units)
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
    #try:
    p.save_if_dirty()
    #except IntegrityError:
        # this handles a userid re-assigned to a different person. That shouldn't happen anymore?
        #print "    Changed userid: " + p.userid
        ## other account with this userid must have been deactivated: update
        #other = Person.objects.get(userid=p.userid)
        #assert other.emplid != p.emplid
        #get_person(other.emplid)
        # try again now
        #p.save()

imported_people = {}
IMPORT_THRESHOLD = 3600*24*7 # import personal info infrequently
NO_USERID_IMPORT_THRESHOLD = 3600*24*2 # import if we don't know their userid yet
def get_person(emplid, commit=True, force=False, grad_data=False):
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
        # should be dead code, since emplid is a unique key in the DB
        raise KeyError("Already duplicate people: %r" % (p_old))
    elif len(p_old)==1:
        p = p_old[0]
    else:
        p = Person(emplid=emplid)
    imported_people[emplid] = p

    if 'lastimport' in p.config:
        import_age = time.time() - p.config['lastimport']
    else:
        import_age = IMPORT_THRESHOLD * 2

    # active students with no userid: pay more attention to try to get their userid for login/email.
    if p.userid is None and import_age > NO_USERID_IMPORT_THRESHOLD:
        new_p = import_person(p, commit=commit, grad_data=grad_data)
        if new_p:
            return new_p
        elif p_old:
            return p

    # only import if data is older than IMPORT_THRESHOLD (unless forced)
    # Randomly occasionally import anyway, so new students don't stay bunched-up.
    elif not force and import_age < IMPORT_THRESHOLD and random.random() < 0.99:
        return p

    # actually import their data
    else:
        new_p = import_person(p, commit=commit, grad_data=grad_data)
        if new_p:
            return new_p
        elif p_old:
            return p


def get_person_grad(emplid, commit=True, force=False):
    """
    Get/update personal info: does get_person() plus additional info we need for grad students
    """
    p = get_person(emplid, commit=commit, grad_data=True, force=force)
    return p


def get_role_people():
    """
    Force a get_person() on all of those with roles and RA appointments
    """
    roles = Role.objects_fresh.all().select_related('person')
    people = set(r.person for r in roles)

    cutoff = datetime.datetime.now() - datetime.timedelta(days=365)
    ras = RAAppointment.objects.filter(start_date__lte=cutoff).select_related('person')
    people |= set([ra.person for ra in ras])

    for p in people:
        get_person(p.emplid, grad_data=True)


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
    db.execute("SELECT MEETING_TIME_START, MEETING_TIME_END, FACILITY_ID, MON,TUES,WED,THURS,FRI,SAT,SUN, "
               "START_DT, END_DT, STND_MTG_PAT, CLASS_SECTION FROM PS_CLASS_MTG_PAT "
               "WHERE CRSE_ID=%s AND CLASS_SECTION LIKE %s AND STRM=%s",
               ("%06i" % (int(offering.crse_id)), offering.section[0:2]+"%", offering.semester.name))
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()
    
    for start,end, room, mon,tues,wed,thurs,fri,sat,sun, start_dt,end_dt, stnd_mtg_pat, class_section in db:
        # dates come in as strings from DB2/reporting DB
        if not start or not end:
            # some meeting times exist with no start/end time
            continue
        start = start.time()
        end = end.time()
        start_dt = start_dt.date()
        end_dt = end_dt.date()

        wkdays = [n for n, day in zip(list(range(7)), (mon,tues,wed,thurs,fri,sat,sun)) if day=='Y']
        labtut_section, mtg_type = fix_mtg_info(class_section, stnd_mtg_pat)
        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=offering, weekday=wkd, start_day=start_dt, end_day=end_dt, start_time=start, end_time=end, labtut_section=labtut_section, room=room)
            if len(m_old)>1:
                raise KeyError("Already duplicate meeting: %r" % (m_old))
            elif len(m_old)==1:
                # new data: just replace.
                m_old = m_old[0]
                if m_old.room==room and m_old.meeting_type==mtg_type and m_old.labtut_section==labtut_section:
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


def has_letter_activities(offering):
    key = 'has-letter-' + offering.slug
    res = cache.get(key)
    if res is not None:
        return res
    else:
        las = LetterActivity.objects.filter(offering=offering, deleted=False)
        res = las.count() > 0
        cache.set(key, res, 12*60*60)


def ensure_member(person, offering, role, cred, added_reason, career, labtut_section=None, grade=None, sched_print_instr=None):
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
            raise KeyError("Already duplicate entries: %r" % (m_old))
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

    # record official grade if we have it (and might need it)
    if has_letter_activities(m.offering):
        m.official_grade = grade or None
    else:
        m.official_grade = None

    # record sched_print_instr status for instructors
    if role=='INST' and sched_print_instr:
        m.config['sched_print_instr'] = sched_print_instr == 'Y'

    # if offering is being given lab/tutorial sections, flag it as having them
    # there must be some way to detect this in ps_class_tbl, but I can't see it.
    if labtut_section and not offering.labtut():
        offering.set_labtut(True)
        offering.save_if_dirty()
    
    m.save_if_dirty()
    return m

@transaction.atomic
def import_instructors(offering):
    "Import instructors for this offering"
    Member.objects.filter(added_reason="AUTO", offering=offering, role="INST").update(role='DROP')
    db = SIMSConn()
    db.execute("SELECT EMPLID, INSTR_ROLE, SCHED_PRINT_INSTR FROM PS_CLASS_INSTR WHERE " \
               "CRSE_ID=%s AND CLASS_SECTION=%s AND STRM=%s AND INSTR_ROLE IN ('PI', 'SI')",
               ("%06i" % (int(offering.crse_id)), offering.section, offering.semester.name))
    for emplid, _, sched_print_instr in db.rows():
        if not emplid:
            continue
        p = get_person(emplid)
        ensure_member(p, offering, "INST", 0, "AUTO", "NONS", sched_print_instr=sched_print_instr)


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
    query = "SELECT S.EMPLID, C2.CLASS_SECTION " \
        "FROM PS_CLASS_TBL C1, PS_CLASS_TBL C2, PS_STDNT_ENRL S " \
        "WHERE C1.SUBJECT=C2.SUBJECT AND C1.CATALOG_NBR=C2.CATALOG_NBR AND C2.STRM=C1.STRM " \
        "AND S.CLASS_NBR=C2.CLASS_NBR AND S.STRM=C2.STRM AND S.ENRL_STATUS_REASON IN ('ENRL','EWAT') " \
        "AND C1.CLASS_NBR=%s AND C1.STRM=%s AND C2.CLASS_SECTION LIKE %s"
    db.execute(query, (offering.class_nbr, offering.semester.name, offering.section[0:2]+"%"))
    labtut = {}
    for emplid, section in db:
        if section == offering.section:
            # not interested in lecture section now.
            continue
        labtut[emplid] = section

    # import actual enrolments
    db.execute("SELECT E.EMPLID, E.ACAD_CAREER, E.UNT_TAKEN, E.CRSE_GRADE_OFF, R.CRSE_GRADE_INPUT "
               "FROM PS_STDNT_ENRL E LEFT JOIN PS_GRADE_ROSTER R "
               "ON E.STRM=R.STRM AND E.ACAD_CAREER=R.ACAD_CAREER AND E.EMPLID=R.EMPLID AND E.CLASS_NBR=R.CLASS_NBR "
               "WHERE E.CLASS_NBR=%s AND E.STRM=%s AND E.STDNT_ENRL_STATUS='E' and "
               "E.ENRL_STATUS_REASON IN ('ENRL','EWAT')", (offering.class_nbr, offering.semester.name))
    for emplid, acad_career, unt_taken, grade_official, grade_roster in db.rows():
        p = get_person(emplid)
        sec = labtut.get(emplid, None)
        grade = grade_official or grade_roster
        ensure_member(p, offering, "STUD", unt_taken, "AUTO", acad_career, labtut_section=sec, grade=grade)

    # Record drop date so the discipline app can display "students who have dropped, but not too long ago".
    # find dropped students in SIMS
    query = """SELECT E.EMPLID, E.ENRL_DROP_DT FROM PS_STDNT_ENRL E
        WHERE E.CLASS_NBR=%s AND E.STRM=%s
        AND E.ENRL_STATUS_REASON NOT IN ('ENRL','EWAT') AND E.ENRL_DROP_DT IS NOT NULL"""
    db.execute(query, (offering.class_nbr, offering.semester.name))
    drop_dates = dict(db)
    emplids = drop_dates.keys()

    # find corresponding Members and record drop date
    members = Member.objects.filter(offering=offering, person__emplid__in=emplids).select_related('person')
    for m in members:
        d = drop_dates[str(m.person.emplid)].isoformat()
        m.config['drop_date'] = d
        m.save_if_dirty()


def import_offering_members(offering, students=True):
    """
    Import all data for the course: instructors, TAs, students, meeting times.
    
    students=False used by test/demo importers
    """
    import_instructors(offering)
    if students:
        import_students(offering)
    import_meeting_times(offering)
    if settings.SVN_DB_CONNECT:
        update_offering_repositories(offering)



########################################################################################################################
# Refactored logic to replace import_offering_members


def import_semester_offerings(strm, students=True, extra_where='1=1'):
    offering_map = crseid_offering_map(strm)

    import_all_instructors(strm, extra_where=extra_where, offering_map=offering_map)
    if students:
        import_all_students(strm, extra_where=extra_where, offering_map=offering_map)
    import_all_meeting_times(strm, extra_where=extra_where, offering_map=offering_map)
    import_all_offering_repositories(strm)


def crseid_offering_map(strm):
    '''
    Map things-from-SIMS to CourseOfferings we have, to lookup quickly later.
    '''
    # TODO: evaluate this for .select_related
    return {(o.semester.name, "%06i" % (int(o.crse_id)), o.section): o
            for o in CourseOffering.objects.filter(semester__name=strm)}


@transaction.atomic
def import_all_instructors(strm, extra_where='1=1', offering_map=None):
    if not offering_map:
        offering_map = crseid_offering_map(strm)

    Member.objects.filter(added_reason="AUTO", offering__semester__name=strm, role="INST").update(role='DROP')
    db = SIMSConn()
    db.execute("SELECT CRSE_ID, CLASS_SECTION, STRM, EMPLID, INSTR_ROLE, SCHED_PRINT_INSTR FROM PS_CLASS_INSTR WHERE " \
               "STRM=%s AND INSTR_ROLE IN ('PI', 'SI') AND " + extra_where,
               (strm,))

    for crse_id, class_section, strm, emplid, instr_role, sched_print_instr in db.rows():
        if not emplid or (strm, crse_id, class_section) not in offering_map:
            continue
        offering = offering_map[(strm, crse_id, class_section)]
        p = get_person(emplid)
        ensure_member(p, offering, "INST", 0, "AUTO", "NONS", sched_print_instr=sched_print_instr)


@transaction.atomic
def import_all_students(strm, extra_where='1=1', offering_map=None):
    if not offering_map:
        offering_map = crseid_offering_map(strm)

    Member.objects.filter(added_reason="AUTO", offering__semester__name=strm, role="STUD").update(role='DROP')
    db = SIMSConn()

    # TODO: remainder of this function not yet refactored. Needs to be broken up since >200k registrations shouldn't be
    # processed at once.



@transaction.atomic
def import_all_meeting_times(strm, extra_where='1=1', offering_map=None):
    if not offering_map:
        offering_map = crseid_offering_map(strm)

    db = SIMSConn()
    db.execute("""SELECT CRSE_ID, CLASS_SECTION, STRM, MEETING_TIME_START, MEETING_TIME_END, FACILITY_ID, MON,TUES,WED,THURS,FRI,SAT,SUN,
               START_DT, END_DT, STND_MTG_PAT FROM PS_CLASS_MTG_PAT WHERE STRM=%s AND """ + extra_where,
               (strm,))
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()

    for crse_id, class_section, strm, start, end, room, mon, tues, wed, thurs, fri, sat, sun, start_dt, end_dt, stnd_mtg_pat in db:
        try:
            offering = offering_map[(strm, crse_id, class_section)]
        except KeyError:
            continue

        if not start or not end:
            # some meeting times exist with no start/end time
            continue

        start = start.time()
        end = end.time()
        start_dt = start_dt.date()
        end_dt = end_dt.date()

        wkdays = [n for n, day in zip(list(range(7)), (mon, tues, wed, thurs, fri, sat, sun)) if day == 'Y']
        labtut_section, mtg_type = fix_mtg_info(class_section, stnd_mtg_pat)

        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=offering, weekday=wkd, start_time=start, end_time=end,
                                               labtut_section=labtut_section, room=room)
            if len(m_old) > 1:
                raise KeyError("Already duplicate meeting: %r" % (m_old))
            elif len(m_old) == 1:
                # new data: just replace.
                m_old = m_old[0]
                if m_old.start_day == start_dt and m_old.end_day == end_dt and m_old.room == room \
                        and m_old.meeting_type == mtg_type and m_old.labtut_section == labtut_section:
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
    if extra_where == '1=1':
        MeetingTime.objects.filter(offering__semester__name=strm).exclude(id__in=found_mtg).delete()


@transaction.atomic
def import_all_offering_repositories(strm):
    if not settings.SVN_DB_CONNECT:
        return

    for o in CourseOffering.objects.filter(semester__name=strm):
        update_offering_repositories(o)







@transaction.atomic
def import_joint(extra_where='1=1'):
    """
    Find combined sections and set CourseOffering.config['joint_with'] appropriately.
    """
    db = SIMSConn()
    db.execute("SELECT STRM, CLASS_NBR, SCTN_COMBINED_ID FROM PS_SCTN_CMBND C WHERE C.STRM IN %s "
               " AND ("+extra_where+")", (import_semesters(),))

    for k,v in itertools.groupby(db, lambda d: (d[0], d[2])):
        # for each combined offering...
        strm, _ = k
        class_nbrs = [int(class_nbr) for _,class_nbr,_ in v]
        offerings = CourseOffering.objects.filter(semester__name=strm, class_nbr__in=class_nbrs)
        for offering in offerings:
            offering.set_joint_with([o.slug for o in offerings if o != offering])
            offering.save()


def import_combined(import_semesters=import_semesters):
    for combined in CombinedOffering.objects.filter(semester__name__in=import_semesters()):
        combined.create_combined_offering()

def update_grads():
    """
    Update any currently-relevant grad students
    """
    active = GradStudent.objects.filter(current_status__in=STATUS_ACTIVE).select_related('person')
    applicants = GradStudent.objects.filter(current_status__in=STATUS_APPLICANT,
                 updated_at__gt=datetime.datetime.now()-datetime.timedelta(days=7)).select_related('person')
    s = Semester.current().offset(1)
    far_applicants = GradStudent.objects.filter(start_semester__name__gte=s.name).select_related('person')
    for gs in set(itertools.chain(active, applicants, far_applicants)):
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
        print(o)
        import_offering_members(o, students=False)


@cache_by_args
def semester_first_day():
    " First day of classes"
    db = SIMSConn()
    db.execute("""
        SELECT STRM, SESS_BEGIN_DT
        FROM PS_SESSION_TBL
        WHERE ACAD_CAREER='UGRD' AND SESSION_CODE='1'""", ())
    return dict(db)

@cache_by_args
def semester_last_day():
    """
    Dict of strm -> last day of the semester's classes
    """
    # Why 250? Because "SELECT * FROM psxlatitem WHERE fieldname='TIME_PERIOD'"
    db = SIMSConn()
    db.execute("""
        SELECT STRM, END_DT
        FROM PS_SESS_TIME_PEROD
        WHERE TIME_PERIOD=250 AND ACAD_CAREER='UGRD' AND SESSION_CODE='1'""", ())
    return dict(db)

@cache_by_args
def all_holidays():
    db = SIMSConn()
    db.execute("""SELECT HOLIDAY, DESCR FROM PS_HOLIDAY_DATE WHERE HOLIDAY_HRS=24""", ())
    return list(db)

def first_monday(start):
    weekday = start.weekday()
    if weekday < 2:
        # before wednesday: we start this week
        return start - datetime.timedelta(days=weekday)
    else:
        # thursday/friday: this week is a loss
        return start + datetime.timedelta(days=(7-weekday))

def import_admin_email(source, message, subject='data import: intervention required'):
    """
    Message the admins about an import problem. Assumes we're in a context where stdout does us no good.
    """
    mail_admins(subject, '[%s checking in.]\n\n%s' % (source, message))

@transaction.atomic
def import_semester_info(verbose=False, dry_run=False, long_long_ago=False, bootstrap=False):
    """
    Update information on Semester objects from SIMS

    Finding the reference is tricky. Try Googling 'sfu calendar {{year}} "academic dates"'

    long_long_ago: import from the beginning of time
    bootstrap: don't assume Semester.current() will work, for bootstrapping test data creation
    """
    output = []
    semester_start = semester_first_day()
    semester_end = semester_last_day()
    sims_holidays = all_holidays()

    if not bootstrap:
        # we want semesters 5 years into the future: that's a realistic max horizon for grad promises
        current = Semester.current()
        strms = [current.offset_name(i) for i in range(15)]
    else:
        strms = []

    if long_long_ago:
        strms = sorted(list(set(strms) | set(semester_start.keys())))
    semesters = dict((s.name, s) for s in Semester.objects.filter(name__in=strms))

    semester_weeks = itertools.groupby(
                SemesterWeek.objects.filter(semester__name__in=strms).select_related('semester'),
                lambda sw: sw.semester.name)
    semester_weeks = dict((k,list(v)) for k,v in semester_weeks)

    holidays = itertools.groupby(
                Holiday.objects.filter(semester__name__in=strms, holiday_type='FULL').select_related('semester'),
                lambda h: h.semester.name)
    holidays = dict((k,list(v)) for k,v in holidays)

    for strm in strms:
        url = settings.BASE_ABS_URL + reverse('sysadmin:edit_semester', kwargs={'semester_name': strm})

        # Semester object
        try:
            semester = semesters[strm]
        except KeyError:
            semester = Semester(name=strm)
            semesters[strm] = semester
            output.append("Creating %s." % (strm,))

        # class start and end dates
        try:
            start = semester_start[strm].date()
        except KeyError:
            # No data found about this semester: if there's a date already around, honour it
            # Otherwise, guess "same day as this semester last year" which is probably wrong but close.
            start = semester.start
            if not semester.start:
                lastyr = semesters[semester.offset_name(-3)]
                start = lastyr.start.replace(year=lastyr.start.year+1)
                output.append("Guessing start date for %s." % (strm,))

        try:
            end = semester_end[strm].date()
        except KeyError:
            # no classes scheduled yet? Assume 13 weeks exactly
            end = start + datetime.timedelta(days=91)

        if semester.start != start:
            output.append("Changing start date for %s from %s to %s." % (strm, semester.start, start))
            semester.start = start
        if semester.end != end:
            output.append("Changing end date for %s from %s to %s." % (strm, semester.end, end))
            semester.end = end

        if not dry_run:
            semester.save()

        # SemesterWeeks
        weeks = semester_weeks.get(strm, [])
        if not weeks:
            sw = SemesterWeek(semester=semester, week=1, monday=first_monday(start))
            weeks.append(sw)
            assert sw.monday.weekday() == 0
            output.append("Creating week 1 for %s on %s." % (strm, sw.monday))
            if not dry_run:
                sw.save()
        elif weeks[0].monday != first_monday(start):
            sw = weeks[0]
            sw.monday = first_monday(start)
            output.append("Changing first Monday of %s to %s." % (strm, sw.monday))
            if not dry_run:
                sw.save()

        length = semester.end - semester.start
        if not bootstrap and length > datetime.timedelta(days=92) and len(weeks) < 2 \
                and semester.start - datetime.date.today() < datetime.timedelta(days=365):
            # semester is longer than 13 weeks: insist that the user specify reading week reasonably-soon before the semester starts
            message = "Semester %s is long (%s) but has no reading week specified. Please have a look here: %s\n\nYou probably want to enter the Monday of week 5/6/7/8 as the Monday after reading week, a week later than it would otherwise be." % (strm, length, url)
            if verbose:
                output.append('*** ' + message)
            else:
                import_admin_email(source='coredata.importer.import_semester_info', message=message)
        elif not bootstrap:
            # also check that the last day of classes is at a coherent time. Might reveal problems with reading week specification.
            endweek,_ = semester.week_weekday(semester.end, weeks=weeks)
            if endweek not in [12, 13, 14]:
                message = "Semester %s ends in week %i (should be 13 or 14). That's weird. Have a look here to see if things are coherent: %s" % (strm, endweek, url)
                if verbose:
                    output.append('*** ' + message)
                else:
                    import_admin_email(source='coredata.importer.import_semester_info', message=message)

        # Holidays
        hs = holidays.get(strm, [])
        h_start, h_end = Semester.start_end_dates(semester)
        for dt, desc in [(d.date(),h) for d,h in sims_holidays if h_start <= d.date() <= h_end]:
            existing = [h for h in hs if h.date == dt]
            if existing:
                holiday = existing[0]
            else:
                holiday = Holiday(semester=semester, date=dt, holiday_type='FULL')
                output.append("Adding holiday %s on %s." % (desc, dt))

            holiday.description = desc
            if not dry_run:
                holiday.save()

    if verbose:
        print('\n'.join(output))


def import_active_grads_gpas(verbose=False, dry_run=False):
    """
    Update active grads GPAs.  We added this task because it turns out some people care
    more about this than we originally thought.  Let's run this every day instead with just the GPA and credits fields.
    """
    from coredata.queries import more_personal_info
    active_grads = GradStudent.objects.filter(current_status__in=STATUS_GPA).select_related('person')
    for grad in active_grads:
        data = more_personal_info(grad.person.emplid, needed=['ccredits', 'gpa'])
        if verbose:
            print("Updating info for: ", grad.person.name(), " with: ", data)
        grad.person.config.update(data)
        if not dry_run:
            grad.person.save()


def swap_class_nbr(slug1: str, slug2: str):
    """
    Swap the class_nbr values of two offerings: used to fix incorrectly-reused values entered in SIMS when departments
    change section numbers.
    """
    o1 = CourseOffering.objects.get(slug=slug1)
    o2 = CourseOffering.objects.get(slug=slug2)
    cn1 = o1.class_nbr
    cn2 = o2.class_nbr
    with transaction.atomic():
        o1.class_nbr = 99999
        o1.save()
        o2.class_nbr = cn1
        o2.save()
        o1.class_nbr = cn2
        o1.save()
