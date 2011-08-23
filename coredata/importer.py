import sys, os, datetime, string, time, copy
import MySQLdb
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from coredata.models import *
from dashboard.models import NewsItem
from log.models import LogEntry
from django.db import transaction
from django.contrib.sessions.models import Session
from django.conf import settings
today = datetime.date.today()
past_cutoff = today - datetime.timedelta(days=30)
future_cutoff = today + datetime.timedelta(days=120)

# these users will be given sysadmin role (for bootstrapping)
sysadmin = ["ggbaker", "sumo"]

# first term we care even vaguely about in import (further selection happens later too)
FIRSTTERM = "1117"
DATA_WHERE = '((subject="CMPT" or subject="MACM") and strm="1104") or strm>="'+FIRSTTERM+'"'
#DATA_WHERE = 'strm>="'+FIRSTTERM+'"'

# artificial combined sections to create: kwargs for CourseOffering creation,
# plus 'subsections' list of sections we're combining.

try:
    combined_sections = [
        {
            'subject': 'CMPT', 'number': '125', 'section': 'X100',
            'semester': Semester.objects.get(name="1114"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32760, 'class_nbr': 32760,
            'title': 'Intro CS/Progr(combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='1114-cmpt-125-d100'),
                CourseOffering.objects.get(slug='1114-cmpt-126-d100')
            ]
        },
        {
            'subject': 'ENSC', 'number': '100', 'section': 'X100',
            'semester': Semester.objects.get(name="1117"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32761, 'class_nbr': 32761,
            'title': 'Eng.Technology and Society (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2011fa-ensc-100-d1'),
                CourseOffering.objects.get(slug='2011fa-ensc-100w-d1')
            ]
        },
        ]
except CourseOffering.DoesNotExist:
    print "unable to build combined_sections"
    combined_sections = []

import_host = '127.0.0.1'      
import_user = 'ggbaker'
import_name = 'sims'
import_port = 4000
#timezone = "America/Vancouver" # timezone of imported class meeting times

ta_host = '127.0.0.1'      
ta_user = 'ta_data_import'
ta_name = 'ta_data_drop'
ta_port = 4000




def decode(s):
    """
    Turn database string into proper Unicode.
    """
    return s.decode('utf8')

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


@transaction.commit_on_success
def fix_emplid(db):
    """
    Any manually-entered people will have emplid 0000?????.  Update them with the real emplid from the database.
    """
    people = Person.objects.filter(emplid__lt=100000)
    for p in people:
        print " ", p.userid
        db.execute('SELECT emplid FROM amaint.idMap WHERE username=%s', p.userid)
        row = db.fetchone()
        if row:
            emplid, = row
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


@transaction.commit_on_success
def import_offerings(db, DATA_WHERE):
    """
    Import course offerings.  Returns set of CourseOffering objects imported.
    """
    db.execute('SELECT subject, catalog_nbr, class_section, strm, crse_id, class_nbr, ssr_component, descr, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt FROM ps_class_tbl WHERE ' + DATA_WHERE)
    imported_offerings = set()
    for subject, number, section, strm, crse_id, class_nbr, component, title, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt in db:
        # only import for defined semesters.
        semesters = Semester.objects.filter(name=strm)
        if not import_semester(semesters):
            continue
        semester = semesters[0]
        title = decode(title)
        
        graded = section.endswith("00")
        if not graded:
            continue

        # make sure the data is as we expect:
        if not CAMPUSES.has_key(campus):
            raise KeyError, "Unknown campus: %r." % (campus)
        if not COMPONENTS.has_key(component):
            raise KeyError, "Unknown course component: %r." % (component)

        if cancel_dt != "None":
            # mark cancelled sections
            component="CAN"

        c_old = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester)
        if len(c_old)>1:
            raise KeyError, "Already duplicate courses: %r" % (c_old)
        elif len(c_old)==1:
            # already in DB: update things that might have changed
            c_old = c_old[0]
            c_old.crse_id = crse_id
            c_old.class_nbr = class_nbr
            c_old.component = component
            c_old.graded = graded
            c_old.title = title
            c_old.campus = campus
            c_old.enrl_cap = enrl_cap
            c_old.enrl_tot = enrl_tot
            c_old.wait_tot = wait_tot
            c_old.slug = c_old.autoslug() # rebuild slug in case section changes for some reason
            c_old.save()
            imported_offerings.add(c_old)
        else:
	    c_old = CourseOffering.objects.filter(class_nbr=class_nbr, semester=semester)
	    if len(c_old)>1:
		raise KeyError, "Already duplicate courses: %r" % (c_old)
	    elif len(c_old) == 1:
		# already in DB: update things that might have changed
            	c_old = c_old[0]
            	c_old.crse_id = crse_id
            	c_old.class_nbr = class_nbr
		c_old.section = section
            	c_old.component = component
            	c_old.graded = graded
            	c_old.title = title
            	c_old.campus = campus
            	c_old.enrl_cap = enrl_cap
            	c_old.enrl_tot = enrl_tot
            	c_old.wait_tot = wait_tot
            	c_old.slug = c_old.autoslug() # rebuild slug in case section changes for some reason
            	c_old.save()
            	imported_offerings.add(c_old)
            else:
            	# new record: create.
            	c = CourseOffering(subject=subject, number=number, section=section, semester=semester, crse_id=crse_id, class_nbr=class_nbr, component=component, graded=graded, title=title, campus=campus, enrl_cap=enrl_cap, enrl_tot=enrl_tot, wait_tot=wait_tot)
            	c.save()
                imported_offerings.add(c)


    return imported_offerings

imported_people = {}
def get_person(db, emplid):
    """
    Get/update personal info for this emplid and return (updated & saved) Person object.
    """
    global imported_people
    # use imported_people as a cache
    if emplid in imported_people:
        return imported_people[emplid]
    
    db.execute('SELECT username, p.emplid, last_name, first_name, middle_name, pref_first_name FROM ps_personal_data p LEFT JOIN amaint.idMap i ON i.emplid=p.emplid WHERE p.emplid=%s', (emplid,))
    for userid, emplid, last_name, first_name, middle_name, pref_first_name in db:
        last_name = decode(last_name)
        first_name = decode(first_name)
        middle_name = decode(middle_name)
        pref_first_name = decode(pref_first_name)

        if not pref_first_name:
            pref_first_name = first_name
        
        p_old = Person.objects.filter(emplid=emplid)
        if len(p_old)>1:
            raise KeyError, "Already duplicate people: %r" % (p_old)
        elif len(p_old)==1:
            # existing entry: make sure it's updated
            p = p_old[0]
            p.userid = userid
            p.last_name = last_name
            p.first_name = first_name
            p.middle_name = middle_name
            p.pref_first_name = pref_first_name
            p.save()
        else:
            # newly-found person: insert
            p = Person(emplid=emplid, userid=userid, last_name=last_name, first_name=first_name, middle_name=middle_name, pref_first_name=pref_first_name)
            p.save()
        
        imported_people[emplid] = p
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

def import_meeting_times(db, offering):
    """
    Import course meeting times
    """
    db.execute('SELECT meeting_time_start, meeting_time_end, facility_id, mon,tues,wed,thurs,fri,sat,sun, start_dt, end_dt, stnd_mtg_pat, class_section FROM ps_class_mtg_pat WHERE crse_id=%s and class_section like %s and strm=%s', (offering.crse_id, offering.section[0:2]+"%", offering.semester.name))
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()
    
    for start,end, room, mon,tues,wed,thurs,fri,sat,sun, start_dt,end_dt, stnd_mtg_pat, class_section in db:
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








def ensure_member(person, offering, role, credits, added_reason, career, labtut_section=None):
    """
    Make sure this member exists with the right properties.
    """
    m_old = Member.objects.filter(person=person, offering=offering)

    if len(m_old)>1:
        raise KeyError, "Already duplicate instructor entries: %r" % (m_old)
    elif len(m_old)==1:
        m = m_old[0]
        m.role = role
        m.labtut_section = labtut_section
        m.credits = credits
        m.added_reason = added_reason
        m.career = career
    else:
        m = Member(person=person, offering=offering, role=role, labtut_section=labtut_section,
                credits=credits, added_reason=added_reason, career=career)
    
    # if offering is being given lab/tutorial sections, flag it as having them
    # there must be some way to detect this in ps_class_tbl, but I can't see it.
    if labtut_section and not offering.labtut():
        offering.set_labtut(True)
        offering.save()
    
    m.save()
    return m


def import_instructors(db, offering):
    n = db.execute('SELECT emplid, instr_role, sched_print_instr FROM ps_class_instr WHERE crse_id=%s and class_section=%s and strm=%s', (offering.crse_id, offering.section, offering.semester.name))
    
    for emplid, instr_role, print_instr in db:
        p = get_person(db, emplid)
        ensure_member(p, offering, "INST", 0, "AUTO", "NONS")


def import_tas(db, tadb, offering):
    tadb.execute('SELECT emplid FROM ta_data WHERE strm=%s and subject=%s and catalog_nbr REGEXP %s and class_section=%s', (offering.semester.name, offering.subject, unicode(offering.number)+"W?", offering.section[0:2]))
    for emplid, in tadb:
        p = get_person(db, emplid)
        ensure_member(p, offering, "TA", 0, "AUTO", "NONS")


def import_students(db, offering):
    # find any lab/tutorial sections
    n = db.execute('SELECT emplid, class_section FROM ps_stdnt_enrl WHERE subject=%s and catalog_nbr=%s and strm=%s and class_section LIKE %s and stdnt_enrl_status="E"', (offering.subject, offering.number, offering.semester.name, offering.section[0:2]+"%"))
    labtut = {}
    for emplid, section in db:
        if section == offering.section:
            # not interested in lecture section now.
            continue
        labtut[emplid] = section
    
    n = db.execute('SELECT emplid, acad_career, unt_taken FROM ps_stdnt_enrl WHERE class_nbr=%s and strm=%s and class_section=%s and stdnt_enrl_status="E"', (offering.class_nbr, offering.semester.name, offering.section))
    for emplid, acad_career, unt_taken in db:
        p = get_person(db, emplid)
        sec = labtut.get(emplid, None)
        ensure_member(p, offering, "STUD", unt_taken, "AUTO", acad_career, labtut_section=sec)


@transaction.commit_on_success
def import_offering(db, tadb, offering):
    """
    Import all data for the course: instructors, TAs, students, meeting times.
    """
    #print " ", offering
    # drop all automatically-added members: will be re-added later on import
    Member.objects.filter(added_reason="AUTO", offering=offering).update(role='DROP')
    
    import_instructors(db, offering)
    import_tas(db, tadb, offering)
    import_students(db, offering)
    import_meeting_times(db, offering)
    
    
@transaction.commit_on_success
def combine_sections(db):
    """
    Combine sections in the database to co-offered courses look the same.
    """
    for info in combined_sections:
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
        for sub in info['subsections']:
            cap_total += sub.enrl_cap
            tot_total += sub.enrl_tot
            wait_total += sub.wait_tot
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
                    old_m.save()
                else:
                    # new membership: duplicate into combined
                    new_m = Member(offering=course, person=m.person, role=m.role,
                            credits=m.credits, career=m.career, added_reason=m.added_reason)
                    new_m.config['origsection'] = sub.slug
                    new_m.save()

        # update totals        
        course.enrl_cap = cap_total
        course.tot_total = tot_total
        course.wait_total = wait_total
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
            r = Role(person=p, role="SYSA", department="!!!!")
            r.save()


def main():
    global DATA_WHERE, sysadmin
    dbpasswd = raw_input()
    tapasswd = raw_input()

    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=dbpasswd, db=import_name, port=import_port)
    db = dbconn.cursor()
    tadbconn = MySQLdb.connect(host=ta_host, user=ta_user,
             passwd=tapasswd, db=ta_name, port=ta_port)
    tadb = tadbconn.cursor()

    print "fixing any unknown emplids"
    fix_emplid(db)
    
    print "importing course offering list"
    offerings = import_offerings(db, DATA_WHERE)
    offerings = list(offerings)
    offerings.sort()

    print "importing course members"
    for o in offerings:
        import_offering(db, tadb, o)
        time.sleep(0.5)
    
    print "combining joint offerings"
    combine_sections(db)
    
    print "giving sysadmin permissions"
    give_sysadmin(sysadmin)
    
    # cleanup sessions table
    Session.objects.filter(expire_date__lt=datetime.datetime.now()).delete()
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=120)).delete()
    # cleanup old log entries
    LogEntry.objects.filter(datetime__lt=datetime.datetime.now()-datetime.timedelta(days=365)).delete()
    # cleanup already-run Celery jobs
    if settings.USE_CELERY:
        import djkombu.models
        #djkombu.models.Message.objects.cleanup()
    
    print "People:", len(imported_people)
    print "Course Offerings:", len(offerings)


if __name__ == "__main__":
    main()

