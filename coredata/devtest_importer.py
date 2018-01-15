# coding=utf-8

# importer to create fake data for development
# suggestion execution:
#   rm db.sqlite && ./manage.py migrate && cp db.sqlite db.empty
#   rm fixtures/*; cp db.empty db.sqlite && python coredata/devtest_importer.py

import os, sys, socket
from django.core.wsgi import get_wsgi_application
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

from django.conf import settings
from django.core import serializers
from coredata.models import Person, Unit, Role, Semester, SemesterWeek, Holiday, CourseOffering, Course, Member, \
    MeetingTime, CAMPUS_CHOICES, VISA_STATUSES
from coredata.importer import import_semester_info, import_offerings, import_offering_members, ensure_member
from coredata.queries import add_person, SIMSConn, cache_by_args
from grades.models import NumericActivity
from privacy.models import set_privacy_signed
from courselib.testing import TEST_COURSE_SLUG
import itertools, random, string
import datetime, time

SEMESTER_CUTOFF = '1100' # semesters with label >= this will be included
role_expiry = datetime.date.today() + datetime.timedelta(days=1000)

def import_strms():
    s = Semester.current()
    return [s.name, s.offset_name(1), s.offset_name(2)]

def test_semester():
    return Semester.current().offset(1)



def fake_emplids():
    """
    Replace student numbers with fakes
    """
    people = Person.objects.all()
    fake = 200000100
    for p in people:
        p.emplid = fake
        if 'lastimport' in p.config: # no need for this in the JSON
            del p.config['lastimport']
        p.save()
        fake += 1

def randname(l):
    """
    Generate a random not-very-name-like string.
    """
    n = random.choice(string.ascii_uppercase)
    for _ in range(l-1):
        n = n + random.choice(string.ascii_lowercase + 'àêïõú')
    return n

randnullbool = lambda:random.choice((False, True, None))
randbool = lambda:random.choice((False, True))

@cache_by_args
def find_emplid(userid):
    """
    Find emplid from userid by looking at email addresses: incorrect in general but works for the few people needed here.
    """
    db = SIMSConn()
    db.execute("""SELECT emplid FROM ps_email_addresses WHERE email_addr=%s""", (userid+'@sfu.ca',))
    return db.fetchone()[0]

@cache_by_args
def guess_userid(emplid):
    """
    Find userid from emplid by looking at email addresses: incorrect in general but works enough for some test data.
    """
    db = SIMSConn()
    db.execute("""SELECT email_addr FROM ps_email_addresses WHERE emplid=%s AND email_addr LIKE '%%@sfu.ca %%'""", (emplid,))
    row = db.fetchone()
    if row:
        email = row[0]
        return email[:-7]


def find_person(userid):
    """
    Find a this person, creating if necessary.
    """
    people = Person.objects.filter(userid=userid)
    if people:
        return people[0]
    else:
        emplid = find_emplid(userid)
        p = add_person(emplid, commit=False)
        p.userid = userid
        p.save()
        return p


def create_true_core():
    """
    Just enough data to bootstrap a minimal environment.
    """
    import_semester_info(dry_run=False, verbose=False, long_long_ago=True, bootstrap=True)
    p = find_person('ggbaker')
    p.emplid = '200000100'
    p.first_name = 'Gregorʏ'
    p.pref_first_name = 'Greg'
    p.save()
    u = Unit(label='UNIV', name='Simon Fraser University')
    u.save()
    r = Role(person=p, role='SYSA', unit=u, expiry=role_expiry)
    r.save()

    return itertools.chain(
        Semester.objects.filter(name__gt=SEMESTER_CUTOFF),
        Person.objects.filter(userid='ggbaker'),
        Unit.objects.all(),
        Role.objects.all(),
    )

def create_units():
    univ = Unit.objects.get(slug='univ')
    fas = Unit(label='FAS', name='Faculty of Applied Sciences', parent=univ)
    fas.save()
    ensc = Unit(label='ENSC', name='School of Engineering Science', parent=fas, acad_org='ENG SCI')
    ensc.save()
    mse = Unit(label='MSE', name='School of Mechatronic Systems Engineering', parent=fas, acad_org='MECH SYS')
    mse.save()
    cmpt = Unit(label='CMPT', name='School of Computing Science', parent=fas, acad_org='COMP SCI')
    cmpt.set_address(['9971 Applied Sciences Building', '8888 University Drive, Burnaby, BC', 'Canada V5A 1S6'])
    cmpt.set_email('csdept@sfu.ca')
    cmpt.set_web('http://www.cs.sfu.ca/')
    cmpt.set_tel('778-782-4277')
    cmpt.set_fax('778-782-3045')
    cmpt.set_informal_name('Computing Science')
    cmpt.set_deptid('12345')
    cmpt.save()


def create_coredata():
    """
    Create enough of the coredata.models stuff to run basic tests
    """
    create_units()

    # restore ggbaker's real emplid so import_offerings will match
    p = find_person('ggbaker')
    p.emplid = find_emplid('ggbaker')

    # import a few more people we definitely need later
    find_person('popowich')
    find_person('dixon')
    find_person('diana')
    find_person('dzhao')
    find_person('pba7')

    # import a limited set of course offerings
    offerings = import_offerings(import_semesters=import_strms, extra_where=
        "(subject='CMPT' AND (catalog_nbr LIKE '%% 12%%')) "
        "OR (subject='CMPT' AND (catalog_nbr LIKE '%% 16%%')) "
        "OR (subject='ENSC' AND (catalog_nbr LIKE '%% 10%%')) "
        )
    offerings = list(offerings)
    offerings.sort()

    if not CourseOffering.objects.filter(slug=TEST_COURSE_SLUG):
        o = CourseOffering.objects.filter(subject='CMPT', semester__name=import_strms()[0]) \
            .order_by('number', 'section').first()
        raise ValueError("courselib.testing.TEST_COURSE_SLUG isn't an offering we have. Maybe use '%s'." % (o.slug))

    # import instructors
    for o in offerings:
        import_offering_members(o, students=False)

    # try to guess instructors' userids
    for p in Person.objects.filter(userid__isnull=True):
        p.userid = guess_userid(p.emplid)
        p.save()

    fake_emplids()

    # use/import no real emplids after this

    # create some fake undergrad/grad students
    for i in range(20):
        userid = "0aaa%i" % (i)
        fname = randname(8)
        p = random.randint(1,2)
        if p == 1:
            pref = fname[:4]
        else:
            pref = fname
        p = Person(emplid=300000300+i, userid=userid, last_name='Student', first_name=fname, middle_name=randname(6), pref_first_name=pref)
        p.save()

        userid = "0ggg%i" % (i)
        fname = randname(8)
        p = random.randint(1,2)
        if p == 1:
            pref = fname[:4]
        else:
            pref = fname
        p = Person(emplid=300000500+i, userid=userid, last_name='Grad', first_name=fname, middle_name=randname(6), pref_first_name=pref)
        p.config['gender'] = random.choice(('M','F','U'))
        p.config['gpa'] = round(random.triangular(0.0, 4.33, 2.33), 2)
        p.config['visa'] = random.choice([x for x,_ in VISA_STATUSES])
        p.config['citizen'] = random.choice(('Canadian', 'OtherCountrian'))
        p.save()

    # some memberships/roles/etc assumed by tests
    o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
    ensure_member(Person.objects.get(userid='ggbaker'), o, "INST", 0, "AUTO", "NONS")
    ensure_member(Person.objects.get(userid='0ggg0'), o, "TA", 0, "AUTO", "NONS")
    ensure_member(Person.objects.get(userid='0aaa0'), o, "STUD", 3, "AUTO", "UGRD")
    ensure_member(Person.objects.get(userid='0aaa1'), o, "STUD", 3, "AUTO", "UGRD")

    d = Person.objects.get(userid='dzhao')
    set_privacy_signed(d)
    u = Unit.objects.get(slug='cmpt')
    r1 = Role(person=d, role='ADVS', unit=u, expiry=role_expiry)
    r1.save()
    r2 = Role(person=d, role='ADMN', unit=u, expiry=role_expiry)
    r2.save()
    r3 = Role(person=Person.objects.get(userid='pba7'), role='SYSA', unit=Unit.objects.get(slug='univ'), expiry=role_expiry)
    r3.save()
    r4 = Role(person=d, role='INV', unit=u, expiry=role_expiry)
    r4.save()
    r5 = Role(person=d, role='OUTR', unit=u, expiry=role_expiry)
    r5.save()
    r6 = Role(person=d, role='SPAC', unit=u, expiry=role_expiry)
    r6.save()

    # ensures course appears in menu for students
    a = NumericActivity(offering=o, name='Assignmenț 1', short_name='A1', status='URLS', position=1, percent=10,
        max_grade=10, due_date=(o.semester.start + datetime.timedelta(days=60)))
    a.save()

    return itertools.chain(
        SemesterWeek.objects.filter(semester__name__gt=SEMESTER_CUTOFF),
        Unit.objects.all(),
        Course.objects.all(),
        CourseOffering.objects.all(),
        Person.objects.order_by('emplid'),
        Member.objects.all(),
        [r1, r2, r3, r4, r5, a.activity_ptr, a],
    )

def create_test_offering():
    """
    main test course: interesting data for grades, marking, submission, groups
    """
    from grades.models import Activity, LetterActivity, CalNumericActivity, CalLetterActivity
    from submission.models import SubmissionComponent
    from submission.models.code import CodeComponent
    from submission.models.pdf import PDFComponent
    from groups.models import Group, GroupMember
    from marking.models import ActivityComponent

    crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)

    crs.set_labtut(True)
    crs.set_url("http://www.cs.sfu.ca/CC/165/common/")
    crs.set_taemail("cmpt-165-contact@sfu.ca")
    crs.save()

    # create example activities
    a1 = NumericActivity.objects.get(offering=crs, slug='a1')
    a2 = NumericActivity(offering=crs, name="Assignment 2", short_name="A2", status="URLS",
        due_date=crs.semester.start + datetime.timedelta(days=70), percent=10, group=True,
        max_grade=20, position=2)
    a2.set_url("http://www.cs.sfu.ca/CC/165/common/a2")
    a2.save()
    pr = LetterActivity(offering=crs, name="Project", short_name="Proj", status="URLS",
        due_date=crs.semester.start + datetime.timedelta(days=80), percent=40, group=True, position=3)
    pr.save()
    re = LetterActivity(offering=crs, name="Report", short_name="Rep", status="URLS",
        due_date=crs.semester.start + datetime.timedelta(days=81), percent=10, group=False, position=4)
    re.save()
    ex = NumericActivity(offering=crs, name="Final Exam", short_name="Exam", status="URLS",
        due_date=None, percent=30, group=False, max_grade=90, position=5)
    ex.save()
    to = CalNumericActivity(offering=crs, name="Final Percent", short_name="Perc", status="INVI",
        due_date=None, percent=0, group=False, max_grade=100, formula="[[activitytotal]]", position=6)
    to.save()
    to = CalLetterActivity(offering=crs, name="Letter Grade", short_name="Letter", status="INVI",
        due_date=None, percent=0, group=False, numeric_activity=to, position=6)
    to.save()

    # make A1 submittable and markable
    s = CodeComponent(activity=a1, title="Cöde File", description="The code you're submitting.",
        allowed=".py,.java")
    s.save()
    s = PDFComponent(activity=a1, title="Report", description="Report on what you did.",
        specified_filename="report.pdf")
    s.save()

    m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part ➀", description="Part ➀ was done well and seems to work.", position=1, slug='part-1')
    m.save()
    m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part 2", description="Part 2 was done well and seems to work.", position=2)
    m.save()

    # create some groups
    members = list(Member.objects.filter(offering=crs, role='STUD'))
    random.shuffle(members)
    m = members.pop()
    g = Group(name="SomeGroup", courseoffering=crs, manager=m)
    g.save()
    for m in [m, members.pop()]:
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()

    m = members.pop()
    g = Group(name="AnotherGroup", courseoffering=crs, manager=m)
    g.save()
    for m in [m, members.pop(), members.pop()]:
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=pr)
        gm.save()

    return itertools.chain(
        Activity.objects.all(),
        NumericActivity.objects.all(),
        LetterActivity.objects.all(),
        CalNumericActivity.objects.all(),
        CalLetterActivity.objects.all(),
        SubmissionComponent.objects.all(),
        CodeComponent.objects.all(),
        PDFComponent.objects.all(),
        Group.objects.all(),
        GroupMember.objects.all(),
        ActivityComponent.objects.all(),
    )


def create_grades():
    """
    Test data for grades, marking, submission, groups
    """
    undergrads = list(Person.objects.filter(last_name='Student'))
    grads = list(Person.objects.filter(last_name='Grad').exclude(userid='0ggg0'))
    for o in CourseOffering.objects.all():
        # TA
        m = Member(person=random.choice(grads), role='TA', offering=o, credits=0, career='NONS', added_reason='TAC')
        m.config['bu'] = 5
        m.save()

        # students
        if o.slug == TEST_COURSE_SLUG:
            # there are some specific students we need in this offering for the marking/testfiles/* imports
            students = set(random.sample(undergrads, 6) + list(Person.objects.filter(userid__in=['0aaa0', '0aaa1', '0aaa2'])))
        else:
            students = random.sample(undergrads, 4)

        for p in students:
            Member.objects.get_or_create(person=p, role='STUD', offering=o, credits=3, career='UGRD', added_reason='AUTO')

    return itertools.chain(
        Holiday.objects.filter(semester__name__gt=SEMESTER_CUTOFF),
        MeetingTime.objects.all(),
        Member.objects.filter(role__in=['TA', 'STUD']),
        create_test_offering(),
    )


def create_grad():
    """
    Test data for grad, ta, ra
    """
    from grad.models import GradProgram, GradStudent, GradProgramHistory, GradStatus, ScholarshipType, Scholarship, \
        OtherFunding, Promise, GradRequirement, CompletedRequirement, LetterTemplate, GradFlag, GradFlagValue, Supervisor

    cmpt = Unit.objects.get(slug='cmpt')
    ensc = Unit.objects.get(slug='ensc')
    mse = Unit.objects.get(slug='mse')

    # some admin roles
    d = Person.objects.get(userid='dzhao')
    r1 = Role(person=d, role='GRAD', unit=cmpt, expiry=role_expiry)
    r1.save()
    r2 = Role(person=Person.objects.get(userid='popowich'), role="GRPD", unit=cmpt, expiry=role_expiry)
    r2.save()
    roles = [r1, r2]

    # departmental data
    st1 = ScholarshipType(unit=cmpt, name='Scholarship-o-rama', eligible=False)
    st1.save()
    st2 = ScholarshipType(unit=cmpt, name='Generic Scholarship #8', eligible=True)
    st2.save()
    scholarship_types = [st1, st2]

    templates = [
                 {"unit": cmpt,
                  "label": "offer",
                  "content": "Congratulations, {{first_name}}, we would like to offer you admission to the {{program}} program in Computing Science at SFU.\r\n\r\nThis is gööd news. Really."
                  },
                 {"unit": cmpt,
                  "label": "visa",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is currently enrolled as a full time student in the {{program}} in the School of Computing Science at SFU."
                  },
                 {"unit": cmpt,
                  "label": "Funding",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is a student in the School of Computing Science's {{program}} program. {{He_She}} has been employed as follows:\r\n\r\n{% if tafunding %}Teaching assistant responsibilities include providing tutorials, office hours and marking assignments. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ tafunding }}{% endif %}\r\n{% if rafunding %}Research assistants assist/provide research services to faculty. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ rafunding }}{% endif %}\r\n{% if scholarships %}{{title}} {{last_name}} has received the following scholarships:\r\n\r\n{{ scholarships }}{% endif %}\r\n\r\n{{title}} {{last_name}} is making satisfactory progress."
                  },
                 ]
    for data in templates:
        t = LetterTemplate(**data)
        t.save()

    p = GradProgram(unit=cmpt, label='MSc Course', description='MSc Course option')
    p.save()
    p = GradProgram(unit=cmpt, label='MSc Proj', description='MSc Project option')
    p.save()
    p = GradProgram(unit=cmpt, label='MSc Thesis', description='MSc Thesis option')
    p.save()
    p = GradProgram(unit=cmpt, label='PhD', description='Doctor of Philosophy')
    p.save()
    p = GradProgram(unit=cmpt, label='Qualifying', description='Qualifying student')
    p.save()
    p = GradProgram(unit=cmpt, label='Special', description='Special Arrangements')
    p.save()

    gr = GradRequirement(program=p, description='Achieved Speciality')
    gr.save()
    for p in GradProgram.objects.filter(unit=cmpt):
        gr = GradRequirement(program=p, description='Found campus')
        gr.save()

    gf = GradFlag(unit=cmpt, label='Dual Degree Program')
    gf.save()
    gf = GradFlag(unit=cmpt, label='Co-op')
    gf.save()

    grads = list(Person.objects.filter(last_name='Grad'))
    programs = list(GradProgram.objects.all())
    today = datetime.date.today()
    starts = Semester.objects.filter(start__gt=today-datetime.timedelta(1000), start__lt=today)
    supervisors = list(set([m.person for m in Member.objects.filter(role='INST').select_related('person')]))

    # create GradStudents (and associated data) in a vaguely realistic way
    for g in grads + random.sample(grads, 5): # put a few in two programs
        p = random.choice(programs)
        start = random.choice(starts)
        sstart = start.start
        if random.randint(1,2) == 1:
            end = start.offset(random.randint(3,9))
        else:
            end = None
        gs = GradStudent(person=g, program=p, research_area=randname(8)+'ology',
                campus=random.choice([x for x,_ in CAMPUS_CHOICES]), is_canadian=randnullbool())
        gs.save()

        gph = GradProgramHistory(student=gs, program=p, start_semester=start)
        gph.save()
        if random.randint(1,3) == 1:
            p2 = random.choice([p2 for p2 in programs if p != p2 and p.unit == p2.unit])
            gph = GradProgramHistory(student=gs, program=p2, start_semester=start.offset(random.randint(1,4)))
            gph.save()

        s = GradStatus(student=gs, status='COMP', start=start, start_date=sstart-datetime.timedelta(days=100))
        s.save()
        if random.randint(1,4) == 1:
            s = GradStatus(student=gs, status='REJE', start=start, start_date=sstart-datetime.timedelta(days=80))
            s.save()
        else:
            s = GradStatus(student=gs, status='OFFO', start=start, start_date=sstart-datetime.timedelta(days=80))
            s.save()
            s = GradStatus(student=gs, status='ACTI', start=start, start_date=sstart)
            s.save()
            if end:
                if random.randint(1,3):
                    s = GradStatus(student=gs, status='WIDR', start=end, start_date=end.start)
                    s.save()
                else:
                    s = GradStatus(student=gs, status='GRAD', start=end, start_date=end.start)
                    s.save()

        gs.update_status_fields()

        # give some money
        sch = Scholarship(student=gs, scholarship_type=random.choice(scholarship_types))
        sch.amount = 2000
        sch.start_semester = start
        sch.end_semester = start.offset(2)
        sch.save()

        of = OtherFunding(student=gs, semester=start.offset(3))
        of.amount = 1300
        of.description = "Money fell from the sky"
        of.save()

        # promise
        p = Promise(student=gs, start_semester=start, end_semester=start.offset(2), amount=10000)
        p.save()
        p = Promise(student=gs, start_semester=start.offset(3), end_semester=start.offset(5), amount=10000)
        p.save()

        # flags
        if random.randint(1,3) == 1:
            cr = CompletedRequirement(requirement=gr, student=gs, semester=start.offset(1))
            cr.save()

        if random.randint(1,4) == 1:
            gfv = GradFlagValue(flag=gf, student=gs, value=True)
            gfv.save()

        # supervisors
        if random.randint(1,3) != 1:
            p = random.choice(supervisors)
            s = Supervisor(student=gs, supervisor=p, supervisor_type='POT')
            s.save()
            if random.randint(1,2) == 1:
                s = Supervisor(student=gs, supervisor=p, supervisor_type='SEN')
                s.save()
                s = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='COM')
                s.save()

    return itertools.chain(
        roles,
        programs,
        scholarship_types,
        GradRequirement.objects.all(),
        LetterTemplate.objects.all(),
        GradFlag.objects.all(),

        GradStudent.objects.all(),
        GradProgramHistory.objects.all(),
        GradStatus.objects.all(),
        Scholarship.objects.all(),
        OtherFunding.objects.all(),
        Promise.objects.all(),
        CompletedRequirement.objects.all(),
        GradFlagValue.objects.all(),
        Supervisor.objects.all(),
    )



def create_ta_ra():
    """
    Build test data for the ta and ra modules.
    """
    from ta.models import CourseDescription, TAPosting, TAApplication, CoursePreference, TAContract, TACourse
    from ta.models import TAKEN_CHOICES, EXPER_CHOICES
    from ra.models import Account, Project, SemesterConfig, RAAppointment
    from ra.models import HIRING_CATEGORY_CHOICES, HIRING_CATEGORY_DISABLED

    # TAs
    d = Person.objects.get(userid='dzhao')
    unit = Unit.objects.get(slug='cmpt')
    r1 = Role(person=d, role='TAAD', unit=unit, expiry=role_expiry)
    r1.save()
    r2 = Role(person=d, role='FUND', unit=unit, expiry=role_expiry)
    r2.save()

    s = Semester.current().next_semester()
    admin = Person.objects.get(userid='dixon')
    CourseDescription(unit=unit, description="Office/Marking", labtut=False).save()
    CourseDescription(unit=unit, description="Office/Marking/Lab", labtut=True).save()

    a = Account(account_number=12345, position_number=12345, title='MSc TA', unit=unit)
    a.save()
    a = Account(account_number=12346, position_number=12346, title='PhD TA', unit=unit)
    a.save()
    a = Account(account_number=12347, position_number=12347, title='External TA', unit=unit)
    a.save()
    a = Account(account_number=12348, position_number=12348, title='Undergrad TA', unit=unit)
    a.save()

    post = TAPosting(semester=s, unit=unit)
    post.opens = s.start - datetime.timedelta(100)
    post.closes = s.start - datetime.timedelta(20)
    post.set_salary([972,972,972,972])
    post.set_scholarship([135,340,0,0])
    post.set_accounts([Account.objects.get(account_number=12345).id, Account.objects.get(account_number=12346).id, Account.objects.get(account_number=12347).id, Account.objects.get(account_number=12348).id])
    post.set_start(s.start)
    post.set_end(s.end)
    post.set_deadline(s.start - datetime.timedelta(10))
    post.set_payperiods(7.5)
    post.set_contact(admin.id)
    post.set_offer_text("This is **your** TA öffer.\n\nThere are various conditions that are töö numerous to list here.")
    post.save()
    offerings = list(post.selectable_offerings())

    for p in Person.objects.filter(last_name='Grad'):
        app = TAApplication(posting=post, person=p, category=random.choice(['GTA1','GTA2']), current_program='CMPT', sin='123456789',
                            base_units=random.choice([3,4,5]))
        app.save()
        will_ta = []
        for i,o in enumerate(random.sample(offerings, 5)):
            t = random.choice(TAKEN_CHOICES)[0]
            e = random.choice(EXPER_CHOICES)[0]
            cp = CoursePreference(app=app, course=o.course, rank=i+1, taken=t, exper=e)
            cp.save()

            if random.random() < 0.07*(5-i):
                will_ta.append(o)

        if will_ta and random.random() < 0.75:
            c = TAContract(status=random.choice(['NEW','OPN','ACC']))
            c.first_assign(app, post)
            c.save()
            for o in will_ta:
                tac = TACourse(course=o, contract=c, bu=app.base_units)
                tac.description = tac.default_description()
                tac.save()

    # RAs
    s = Semester.current()
    superv = list(m.person for m in Member.objects.filter(role='INST').select_related('person'))
    empl = list(itertools.chain(Person.objects.filter(last_name='Grad'), random.sample(Person.objects.filter(last_name='Student'), 10)))
    cats = [c for c,d in HIRING_CATEGORY_CHOICES if c not in HIRING_CATEGORY_DISABLED]
    config = SemesterConfig.get_config([unit], s)

    acct = Account(account_number=12349, position_number=12349, title='NSERC RA', unit=unit)
    acct.save()
    proj1 = Project(project_number=987654, fund_number=31, unit=unit)
    proj1.save()
    proj2 = Project(project_number=876543, fund_number=13, unit=unit)
    proj2.save()

    for i in range(30):
        p = random.choice(empl)
        s = random.choice(superv)
        c = random.choice(cats)
        freq = random.choice(['B', 'L'])
        if freq == 'B':
            payargs = {'lump_sum_pay': 10000, 'biweekly_pay': 1250, 'pay_periods': 8, 'hourly_pay': 31, 'hours': 40}
        else:
            payargs = {'lump_sum_pay': 4000, 'biweekly_pay': 0, 'pay_periods': 8, 'hourly_pay': 0, 'hours': 0}
        ra = RAAppointment(person=p, sin=123456789, hiring_faculty=s, unit=unit, hiring_category=c,
                           project=random.choice([proj1,proj2]), account=acct, pay_frequency=freq,
                           start_date=config.start_date(), end_date=config.end_date(),
                           **payargs)
        ra.set_use_hourly(random.choice([True, False]))
        ra.save()

    return itertools.chain(
        [r1, r2],
        Account.objects.all(),
        Project.objects.all(),
        SemesterConfig.objects.all(),
        RAAppointment.objects.all(),
        TAPosting.objects.all(),
        CourseDescription.objects.all(),
        TAApplication.objects.all(),
        CoursePreference.objects.all(),
        TAContract.objects.all(),
        TACourse.objects.all(),
    )


def create_onlineforms():
    """
    Build test data for the onlineforms module.
    """
    from onlineforms.models import FormGroup, FormGroupMember, Form, Sheet, Field
    unit = Unit.objects.get(slug='cmpt')
    fg = FormGroup(name="Admins", unit=unit)
    fg.save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='ggbaker')).save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='dzhao')).save()

    f1 = Form(title="Simple Form", owner=fg, unit=fg.unit, description="Simple test form.", initiators='ANY')
    f1.save()
    s1 = Sheet(form=f1, title="Initial sheet")
    s1.save()
    fld1 = Field(label='Favorite Color', sheet=s1, fieldtype='SMTX', config={"min_length": 1, "required": True, "max_length": "100", 'label': 'Favorite Color', "help_text":''})
    fld1.save()
    fld2 = Field(label='Reason', sheet=s1, fieldtype='MDTX', config={"min_length": 10, "required": True, "max_length": "400", 'label': 'Reason', "help_text":'Why?'})
    fld2.save()
    fld3 = Field(label='Second Favorite Color', sheet=s1, fieldtype='SMTX', config={"min_length": 1, "required": False, "max_length": "100", 'label': 'Second Favorite Color', "help_text":''})
    fld3.save()

    f2 = Form(title="Appeal Form", owner=fg, unit=fg.unit, description="An all-purpose appeal form to appeal things with", initiators='LOG', advisor_visible=True)
    f2.save()
    s2 = Sheet(form=f2, title="Student Appeal")
    s2.save()
    fld4 = Field(label='Appeal', sheet=s2, fieldtype='SMTX', config={"min_length": 1, "required": True, "max_length": "100", 'label': 'Appeal', "help_text":'What do you want to appeal?'})
    fld4.save()
    fld4 = Field(label='Reasons', sheet=s2, fieldtype='LGTX', config={"min_length": 1, "required": True, "max_length": "1000", 'label': 'Reasons', "help_text":'Why do you think you deserve it?'})
    fld4.save()
    fld5 = Field(label='Prediction', sheet=s2, fieldtype='RADI', config={"required": False, 'label': 'Predictiŏn', "help_text":"Do you think it's likely this will be approved?", "choice_1": "Yes", "choice_2": "No", "choice_3": "Huh?"})
    fld5.save()
    s3 = Sheet(form=f2, title="Decision", can_view="ALL")
    s3.save()
    fld5 = Field(label='Decision', sheet=s3, fieldtype='RADI', config={"required": True, 'label': 'Decision', "help_text":"Do you approve this appeal?", "choice_1": "Yes", "choice_2": "No", "choice_3": "See comments"})
    fld5.save()
    fld6 = Field(label='Comments', sheet=s3, fieldtype='MDTX', config={"min_length": 1, "required": False, "max_length": "1000", 'label': 'Comments', "help_text":'Any additional comments'})
    fld6.save()

    return itertools.chain(
        FormGroup.objects.all(),
        FormGroupMember.objects.all(),
        Form.objects.all(),
        Sheet.objects.all(),
        Field.objects.all(),
    )


def create_outreach():
    from outreach.models import OutreachEvent, OutreachEventRegistration
    unit = Unit.objects.get(slug='cmpt')
    start = datetime.datetime(2099,0o1,0o1,00,00,00) # Start a long time from now so the tests are always valid
    end = start + datetime.timedelta(days=2)
    e = OutreachEvent(title='A Test Event', start_date=start, end_date=end, unit=unit, notes='Here are some notes',
                      description='An event to test', slug='devtest_a_test_event')
    e.save()
    dob = datetime.date(1800,01,01)
    r = OutreachEventRegistration(event=e, birthdate=dob, parent_name='Joe Smith Sr.', last_name='SomePerson', first_name='Bob',
                                  school='Little Lord Fauntleroy School for Albino Hemophiliacs', grade=2)
    r.save()
    return itertools.chain(
        OutreachEvent.objects.all(),
        OutreachEventRegistration.objects.all(),
    )


def create_sessionals():
    from sessionals.models import SessionalAccount, SessionalContract
    from coredata.models import AnyPerson, Person
    unit = Unit.objects.get(slug='cmpt')
    a = SessionalAccount(unit=unit, title='SFUFA Account', account_number='234', position_number=123456,
                         slug='cmpt-234-sfufa-account')
    a.save()
    p = Person.objects.get(userid='0ggg1')
    ap = AnyPerson.get_or_create_for(person=p)
    ap.save()
    co = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
    c = SessionalContract(account=a, sessional=ap, offering=co, appointment_start=co.semester.start,
                          appointment_end=co.semester.end, pay_start=co.semester.start - datetime.timedelta(days=2),
                          pay_end=co.semester.end - datetime.timedelta(days=2), slug='a-test-sessionalcontract',
                          sin='000000000', contact_hours=45.6, total_salary=4657.95, created_by='devtest', unit=unit)
    c.save()
    return itertools.chain(
        SessionalAccount.objects.all(),
        AnyPerson.objects.all(),
        SessionalContract.objects.all(),
    )


def create_inventory():
    from inventory.models import Asset
    unit = Unit.objects.get(slug='cmpt')
    a = Asset(unit=unit, name='Something', brand='Baycrest', slug='cmpt-something',
              location='In the dining room, with the candlestick')
    a.save()
    return itertools.chain(
        Asset.objects.all(),
    )


def create_space():
    from space.models import RoomType, Location, BookingRecord
    unit = Unit.objects.get(slug='cmpt')
    rt = RoomType(unit=unit, long_description='A room type', code='RMM_TYP',
                  COU_code_description='Magical Room Type Space', space_factor=0.5, COU_code_value=12.2)
    rt.save()
    loc = Location(unit=unit, campus='BRNBY', building='ASB', floor=9, room_number='9971', square_meters=6,
                   room_type=rt, infrastructure='STD', room_capacity=10, category='STAFF', occupancy_count=3,
                   own_or_lease='OWN', comments='This is the room with the thing')
    loc.save()
    p = Person.objects.get(userid='0ggg1')
    start = datetime.datetime(2010,0o1,0o1,00,00,00)
    end = datetime.datetime(2099,0o1,0o1,23,59,59)
    book = BookingRecord(person=p, location=loc, start_time=start, end_time=end)
    book.save()
    return itertools.chain(
        RoomType.objects.all(),
        Location.objects.all(),
        BookingRecord.objects.all()
    )


def serialize_result(data_func, filename):
    print("creating %s.json" % (filename))
    start = time.time()
    objs = data_func()
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open('fixtures/' + filename + '.json', 'w')
    fh.write(data)
    fh.close()
    done = time.time()
    #print "(%.1f s)" % (done-start)

def main():
    assert not settings.DISABLE_REPORTING_DB
    assert settings.SIMS_PASSWORD
    assert Semester.objects.all().count() == 0, "Database must be empty before we start this."

    serialize_result(create_true_core, 'basedata')
    serialize_result(create_coredata, 'coredata')
    # use/import no real emplids after this
    serialize_result(create_grades, 'grades')
    serialize_result(create_grad, 'grad')
    serialize_result(create_onlineforms, 'onlineforms')
    serialize_result(create_ta_ra, 'ta_ra')
    serialize_result(create_outreach, 'outreach')
    serialize_result(create_sessionals, 'sessionals')
    serialize_result(create_inventory, 'inventory')
    serialize_result(create_space, 'space')

if __name__ == "__main__":
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError("Don't do that.")
    main()