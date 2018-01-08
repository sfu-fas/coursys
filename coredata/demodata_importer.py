# do the import with fake data for development

# setup:
#   need courses/secrets.py to have SIMS_USER, SIMS_PASSWORD, EMPLID_API_SECRET
#   ssh -L 127.0.0.1:50000:hutch.ais.sfu.ca:50000 -l ggbaker -N pf.sfu.ca
#   Do reporting DB setup as described in the first set of shell commands: instructions/REPORTING_DATABASE.md

# setup test:
#   from coredata.queries import *
#   emplid_to_userid(00000000)  # pick an emplid with active account; only works from courses.cs and coursys-demo.cs.
#   db = SIMSConn()
#   db.execute("SELECT descr FROM dbcsown.PS_TERM_TBL WHERE strm='1111'", ())
#   list(db)

# suggested execution:
#   echo "drop database coursys; create database coursys;" | mysql -uroot -p
#   echo "CREATE USER 'coursysuser'@'localhost' IDENTIFIED BY 'coursyspassword'; GRANT ALL PRIVILEGES ON coursys_db.* TO 'coursysuser'@'localhost'" | mysql -uroot -p
#   ./manage.py migrate && ./manage.py dbdump
#   python coredata/demodata_importer.py && ./manage.py dbdump
#   ./manage.py rebuild_index

import string, socket, random
from .importer import create_semesters, import_offering_members, import_offerings
from coredata.models import Member, Person, CourseOffering, Semester, SemesterWeek, Unit, Role, CAMPUSES
from courselib.testing import create_fake_semester
import datetime, itertools

import os
from django.core.wsgi import get_wsgi_application
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

NEEDED_SEMESTERS = [1131,1134,1137, 1141,1144,1147, 1151,1154,1157, 1161,1164,1167, 1171,1174,1177, 1181,1184,1187]
IMPORT_SEMESTERS = ('1164', '1167')
TEST_SEMESTER = 1164 # semester for TA/RA demo data

fakes = {}
next_emplid = 100

def fake_emplid(emplid=None):
    """
    Return a fake EMPLID for this person
    """
    global fakes, next_emplid
    base = 200000000
    
    if emplid != None and emplid in fakes:
        return fakes[emplid]
    
    next_emplid += 1
    fake = base + next_emplid
    fakes[emplid] = fake
    return fake

def fake_emplids():
    """
    Replace student numbers with fakes
    """
    people = Person.objects.all()
    for p in people:
        p.emplid = fake_emplid(p.emplid)
        p.save()

def randname(l):
    n = random.choice(string.ascii_uppercase)
    for _ in range(l-1):
        n = n + random.choice(string.ascii_lowercase)
    return n


all_students = {}
def create_fake_students():
    """
    Make a bunch of fake students so we can add them to classes later.
    """
    global all_students
    for lett in string.ascii_lowercase:
        for i in range(11):
            if i==10:
                userid = "0%sgrad" % (lett*3)
                fname = randname(8)
                lname = "Grad"
            else:
                userid = "0%s%i" % (lett*3, i)
                fname = randname(8)
                lname = "Student"
            p = Person(emplid=fake_emplid(), userid=userid, last_name=lname, first_name=fname, middle_name="", pref_first_name=fname[:4])
            p.save()
            all_students[userid] = p

def fill_courses():
    """
    Put 10 students and a TA in each course.
    """
    global all_students
    for crs in CourseOffering.objects.exclude(component="CAN"):
        lett = random.choice(string.ascii_lowercase)
        for i in range(10):
            userid = "0%s%i" % (lett*3, i)
            m = Member(person=all_students[userid], offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO")
            m.save()

        # and the TA
        userid = "0%sgrad" % (lett*3)
        m = Member(person=all_students[userid], offering=crs, role="TA", credits=0, career="NONS", added_reason="AUTO")
        m.save()

def create_classes():
    print("creating fake students")
    create_fake_students()
    print("filling classes with students")
    fill_courses()



def create_others():
    """
    Create other users for the test data set
    """
    p = Person(emplid=fake_emplid(), first_name="Susan", last_name="Kindersley", pref_first_name="sumo", userid="sumo")
    p.save()
    Role(person=p, role="GRPD", unit=Unit.objects.get(slug='cmpt')).save()
    p = Person(emplid=fake_emplid(), first_name="Danyu", last_name="Zhao", pref_first_name="Danyu", userid="dzhao")
    p.save()
    Role(person=p, role="ADVS", unit=Unit.objects.get(slug='cmpt')).save()
    Role(person=p, role="TAAD", unit=Unit.objects.get(slug='cmpt')).save()
    Role(person=p, role="GRAD", unit=Unit.objects.get(slug='cmpt')).save()
    Role(person=p, role="FUND", unit=Unit.objects.get(slug='cmpt')).save()
    Role(person=p, role="ADMN", unit=Unit.objects.get(slug='cmpt')).save()


from grad.models import GradProgram, GradRequirement, GradStudent, ScholarshipType, GradFlag, GradStatus, Supervisor, LetterTemplate
def create_grads():
    """
    Put the grad students created before into GradStudent records.
    """
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='MSc Project', description='MSc Project option')
    gp.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='MSc Thesis', description='MSc Thesis option')
    gp.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='PhD', description='PhD')
    gp.save()
    req = GradRequirement(program=gp, description='Defended Thesis')
    req.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='ensc'), label='MEng', description='Masters in Engineering')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='ensc'), label='PhD', description='PhD')
    gp.save()
    st = ScholarshipType(unit=Unit.objects.get(slug='cmpt'), name="Some Scholarship")
    st.save()
    gf = GradFlag(unit=Unit.objects.get(slug='cmpt'), label='Special Specialist Program')
    gf.save()

    programs = list(GradProgram.objects.all())
    supervisors = list(set([m.person for m in Member.objects.filter(offering__owner__slug='cmpt', role='INST')]))
    for p in Person.objects.filter(userid__endswith='grad'):
        gp = random.choice(programs)
        campus = random.choice(list(CAMPUSES))
        gs = GradStudent(person=p, program=gp, campus=campus)
        gs.save()

        startsem = random.choice(list(Semester.objects.filter(name__lt=Semester.current().name)))
        st = GradStatus(student=gs, status='COMP', start=startsem)
        st.save()
        st = GradStatus(student=gs, status=random.choice(['ACTI', 'ACTI', 'LEAV']), start=startsem.next_semester())
        st.save()
        if random.random() > 0.5:
            st = GradStatus(student=gs, status=random.choice(['GRAD', 'GRAD', 'WIDR']), start=startsem.next_semester().next_semester().next_semester())
            st.save()

        if random.random() > 0.25:
            sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='SEN')
            sup.save()
            sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='COM')
            sup.save()
            if random.random() > 0.5:
                sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='COM')
                sup.save()
            else:
                sup = Supervisor(student=gs, external="Some External Supervisor", supervisor_type='COM', config={'email': 'external@example.com'})
                sup.save()
        # TODO: completed requirements, letter templates and letters

def create_grad_templ():
    templates = [
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "offer",
                  "content": "Congratulations, {{first_name}}, we would like to offer you admission to the {{program}} program in Computing Science at SFU.\r\n\r\nThis is good news. Really."
                  },
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "visa",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is currently enrolled as a full time student in the {{program}} in the School of Computing Science at SFU."
                  },
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "Funding",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is a student in the School of Computing Science's {{program}} program. {{He_She}} has been employed as follows:\r\n\r\n{% if tafunding %}Teaching assistant responsibilities include providing tutorials, office hours and marking assignments. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ tafunding }}{% endif %}\r\n{% if rafunding %}Research assistants assist/provide research services to faculty. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ rafunding }}{% endif %}\r\n{% if scholarships %}{{title}} {{last_name}} has received the following scholarships:\r\n\r\n{{ scholarships }}{% endif %}\r\n\r\n{{title}} {{last_name}} is making satisfactory progress."
                  },
                 ]
    for data in templates:
        t = LetterTemplate(**data)
        t.save()

from ta.models import CourseDescription, TAPosting, TAApplication, CoursePreference, TAContract, TACourse, TAKEN_CHOICES, EXPER_CHOICES
def create_ta_data():
    unit = Unit.objects.get(slug='cmpt')
    s = Semester.objects.get(name=TEST_SEMESTER).next_semester()
    admin = Person.objects.get(userid='dixon')
    CourseDescription(unit=unit, description="Office/Marking", labtut=False).save()
    CourseDescription(unit=unit, description="Office/Marking/Lab", labtut=True).save()

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
    post.set_offer_text("This is **your** TA offer.\n\nThere are various conditions that are too numerous to list here.")
    post.save()
    offerings = list(post.selectable_offerings())

    for p in Person.objects.filter(userid__endswith='grad'):
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

from ra.models import Account, Project, SemesterConfig, RAAppointment, HIRING_CATEGORY_CHOICES, HIRING_CATEGORY_DISABLED
from grad.forms import possible_supervisor_people

def create_ra_data():
    unit = Unit.objects.get(slug='cmpt')
    s = Semester.objects.get(name=TEST_SEMESTER)
    superv = list(possible_supervisor_people([unit]))
    empl = list(itertools.chain(Person.objects.filter(userid__endswith='grad'), random.sample(Person.objects.filter(last_name='Student'), 10)))
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


from discipline.models import DisciplineTemplate
from dashboard.models import UserConfig
def create_more_data():
    """
    More data for the unit tests and general usabilty of a test system
    """
    templates = [
                 {"field": "contact_email_text",
                  "label": "generic",
                  "text": "DESCRIPTION OF INCIDENT. This does not usually occur unless there is a violation of SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "contact_email_text",
                  "label": "not your work",
                  "text": "Your submission for {{ACTIVITIES}} contains work that does not appear to be your own. This indicates that there is a violation of SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "facts",
                  "label": "attachment",
                  "text": "See details in attached file facts.pdf."},
                 {"field": "contact_email_text",
                  "label": "simiar work (group)",
                  "text": "You and other students submitted very similar work on {{ACTIVITIES}}. This level of similarity does not usually occur unless collaboration exceeds the limits allowed by SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "facts",
                  "label": "copied (other knew)",
                  "text": "{{FNAME}} was given a solution to {{ACTIVITIES}} by another student. The other student seems to have completed the work independently. Both students submitted the work as their own."},
                 {"field": "facts",
                  "label": "copied (without knowledge)",
                  "text": "{{FNAME}} copied the work of another student on {{ACTIVITIES}} without his/her knowledge.  Both students submitted the work as their own."},
                 {"field": "meeting_summary",
                  "label": "admitted",
                  "text": "The student admitted academic dishonesty as described below in \u201cfacts of the case\u201d."},
                 {"field": "meeting_summary",
                  "label": "quote email",
                  "text": "The student explained the situation in his/her email:\r\n\r\nbq. PASTE QUOTE HERE"},
                 {"field": "meeting_summary",
                  "label": "explained",
                  "text": "{{FNAME}} explained that..."},
                 ]
    for data in templates:
        t = DisciplineTemplate(**data)
        t.save()

    cmpt = Unit.objects.get(slug='cmpt')
    a = Account(account_number=12345, position_number=12345, title='MSc TA', unit=cmpt)
    a.save()
    a = Account(account_number=12346, position_number=12346, title='PhD TA', unit=cmpt)
    a.save()
    a = Account(account_number=12347, position_number=12347, title='External TA', unit=cmpt)
    a.save()
    a = Account(account_number=12348, position_number=12348, title='Undergrad TA', unit=cmpt)
    a.save()

    uc = UserConfig(user=Person.objects.get(userid='dzhao'), key='advisor-token', value={'token': '30378700c0091f34412ec9a082dca267'})
    uc.save()
    uc = UserConfig(user=Person.objects.get(userid='ggbaker'), key='advisor-token', value={'token': '082dca26730378700c0091f34412ec9a'})
    uc.save()
    p = Person(userid='probadmn', emplid='200002387', first_name='Problem', last_name='Admin')
    p.save()
    uc = UserConfig(user=p, key='problems-token', value={'token': '30378700c0091f34412ec9a082dca268'})
    uc.save()

    p = Person(userid='teachadm', emplid='200002388', first_name='Teaching', last_name='Admin')
    p.save()
    r = Role(person=p, role="TADM", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    #sp = SemesterPlan(semester=Semester.objects.get(name=TEST_SEMESTER), name='Test Plan', unit=Unit.objects.get(slug='cmpt'), slug='test-plan')
    #sp.save()
    #o = PlannedOffering(plan=sp, course=Course.objects.get(slug='cmpt-102'), section='D100', campus='BRNBY', enrl_cap=100)
    #o.save()
    #PlanningCourse.create_for_unit(Unit.objects.get(slug='cmpt'))
    #te = TeachingEquivalent(pk=1, instructor=Person.objects.get(userid='ggbaker'), semester=Semester.objects.get(name=TEST_SEMESTER), credits_numerator=1, credits_denominator=1, summary="Foo", status='UNCO')
    #te.save()
    #ti = TeachingIntention(instructor=Person.objects.get(userid='ggbaker'), semester=Semester.objects.get(name=TEST_SEMESTER), count=2)
    #ti.save()
    #tc = TeachingCapability(instructor=Person.objects.get(userid='ggbaker'), course=Course.objects.get(slug='cmpt-102'), note='foo')
    #tc.save()

    p = Person(userid='classam', emplid='200002389', first_name='Curtis', last_name='Lassam')
    p.save()
    r = Role(person=p, role="TECH", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=p, role="SYSA", unit=Unit.objects.get(slug='cmpt'))
    r.save()

    # create some faculty roles
    members = Member.objects.filter(role='INST', offering__owner__slug='cmpt')
    instr = set(m.person for m in members)
    faculty = random.sample(instr, 10)
    for p in faculty:
        Role(person=p, role='FAC', unit=cmpt).save()



from onlineforms.models import FormGroup, FormGroupMember, Form, Sheet, Field
def create_form_data():
    unit = Unit.objects.get(slug='cmpt')
    fg = FormGroup(name="Admins", unit=unit)
    fg.save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='ggbaker')).save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='classam')).save()

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
    fld5 = Field(label='Prediction', sheet=s2, fieldtype='RADI', config={ "required": False, 'label': 'Prediction', "help_text":"Do you think it's likely this will be approved?", "choice_1": "Yes", "choice_2": "No", "choice_3": "Huh?"})
    fld5.save()
    s3 = Sheet(form=f2, title="Decision", can_view="ALL")
    s3.save()
    fld5 = Field(label='Decision', sheet=s3, fieldtype='RADI', config={ "required": True, 'label': 'Decision', "help_text":"Do you approve this appeal?", "choice_1": "Yes", "choice_2": "No", "choice_3": "See comments"})
    fld5.save()
    fld6 = Field(label='Comments', sheet=s3, fieldtype='MDTX', config={"min_length": 1, "required": False, "max_length": "1000", 'label': 'Comments', "help_text":'Any additional comments'})
    fld6.save()




from grad.models import GradProgram, GradRequirement, GradStudent, ScholarshipType, GradFlag, GradStatus, Supervisor, LetterTemplate
def create_grads():
    """
    Put the grad students created before into GradStudent records.
    """
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='MSc Project', description='MSc Project option')
    gp.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='MSc Thesis', description='MSc Thesis option')
    gp.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='cmpt'), label='PhD', description='PhD')
    gp.save()
    req = GradRequirement(program=gp, description='Defended Thesis')
    req.save()
    req = GradRequirement(program=gp, description='Formed Committee')
    req.save()
    gp = GradProgram(unit=Unit.objects.get(slug='ensc'), label='MEng', description='Masters in Engineering')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='ensc'), label='PhD', description='PhD')
    gp.save()
    st = ScholarshipType(unit=Unit.objects.get(slug='cmpt'), name="Some Scholarship")
    st.save()
    gf = GradFlag(unit=Unit.objects.get(slug='cmpt'), label='Special Specialist Program')
    gf.save()

    programs = list(GradProgram.objects.all())
    supervisors = list(set([m.person for m in Member.objects.filter(offering__owner__slug='cmpt', role='INST')]))
    for p in Person.objects.filter(userid__endswith='grad'):
        gp = random.choice(programs)
        campus = random.choice(list(CAMPUSES))
        gs = GradStudent(person=p, program=gp, campus=campus)
        gs.save()

        startsem = random.choice(list(Semester.objects.filter(name__lt=Semester.current().name)))
        st = GradStatus(student=gs, status='COMP', start=startsem)
        st.save()
        st = GradStatus(student=gs, status=random.choice(['ACTI', 'ACTI', 'LEAV']), start=startsem.next_semester())
        st.save()
        if random.random() > 0.5:
            st = GradStatus(student=gs, status=random.choice(['GRAD', 'GRAD', 'WIDR']), start=startsem.next_semester().next_semester().next_semester())
            st.save()

        if random.random() > 0.25:
            sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='SEN')
            sup.save()
            sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='COM')
            sup.save()
            if random.random() > 0.5:
                sup = Supervisor(student=gs, supervisor=random.choice(supervisors), supervisor_type='COM')
                sup.save()
            else:
                sup = Supervisor(student=gs, external="Some External Supervisor", supervisor_type='COM', config={'email': 'external@example.com'})
                sup.save()
        # TODO: completed requirements, letter templates and letters

def create_grad_templ():
    templates = [
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "offer",
                  "content": "Congratulations, {{first_name}}, we would like to offer you admission to the {{program}} program in Computing Science at SFU.\r\n\r\nThis is good news. Really."
                  },
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "visa",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is currently enrolled as a full time student in the {{program}} in the School of Computing Science at SFU."
                  },
                 {"unit": Unit.objects.get(slug='cmpt'),
                  "label": "Funding",
                  "content": "This is to confirm that {{title}} {{first_name}} {{last_name}} is a student in the School of Computing Science's {{program}} program. {{He_She}} has been employed as follows:\r\n\r\n{% if tafunding %}Teaching assistant responsibilities include providing tutorials, office hours and marking assignments. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ tafunding }}{% endif %}\r\n{% if rafunding %}Research assistants assist/provide research services to faculty. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ rafunding }}{% endif %}\r\n{% if scholarships %}{{title}} {{last_name}} has received the following scholarships:\r\n\r\n{{ scholarships }}{% endif %}\r\n\r\n{{title}} {{last_name}} is making satisfactory progress."
                  },
                 ]
    for data in templates:
        t = LetterTemplate(**data)
        t.save()

from ta.models import CourseDescription, TAPosting, TAApplication, CoursePreference, TAContract, TACourse, TAKEN_CHOICES, EXPER_CHOICES
def create_ta_data():
    unit = Unit.objects.get(slug='cmpt')
    s = Semester.objects.get(name=TEST_SEMESTER).next_semester()
    admin = Person.objects.get(userid='dixon')
    CourseDescription(unit=unit, description="Office/Marking", labtut=False).save()
    CourseDescription(unit=unit, description="Office/Marking/Lab", labtut=True).save()

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
    post.set_offer_text("This is **your** TA offer.\n\nThere are various conditions that are too numerous to list here.")
    post.save()
    offerings = list(post.selectable_offerings())

    for p in Person.objects.filter(userid__endswith='grad'):
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

from ra.models import Account, Project, SemesterConfig, RAAppointment, HIRING_CATEGORY_CHOICES, HIRING_CATEGORY_DISABLED
from grad.forms import possible_supervisor_people

def create_ra_data():
    unit = Unit.objects.get(slug='cmpt')
    s = Semester.objects.get(name=TEST_SEMESTER)
    superv = list(possible_supervisor_people([unit]))
    empl = list(itertools.chain(Person.objects.filter(userid__endswith='grad'), random.sample(Person.objects.filter(last_name='Student'), 10)))
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


from discipline.models import DisciplineTemplate
from dashboard.models import UserConfig
def create_more_data():
    """
    More data for the unit tests and general usabilty of a test system
    """
    templates = [
                 {"field": "contact_email_text",
                  "label": "generic",
                  "text": "DESCRIPTION OF INCIDENT. This does not usually occur unless there is a violation of SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "contact_email_text",
                  "label": "not your work",
                  "text": "Your submission for {{ACTIVITIES}} contains work that does not appear to be your own. This indicates that there is a violation of SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "facts",
                  "label": "attachment",
                  "text": "See details in attached file facts.pdf."},
                 {"field": "contact_email_text",
                  "label": "simiar work (group)",
                  "text": "You and other students submitted very similar work on {{ACTIVITIES}}. This level of similarity does not usually occur unless collaboration exceeds the limits allowed by SFU's Code of Academic Integrity and Good Conduct, Policy S10.01. I take academic honesty very seriously and intend to pursue this apparent violation of SFU's standards for academic honesty.\r\n\r\nAs required by SFU Policy S10.02, Principles and Procedures for Academic Discipline, I am offering you the opportunity to meet with me to discuss this incident. You are not required to accept this offer. If you would like to meet, please contact me to make an appointment outside of my regular office hours.\r\n\r\nYou may wish to refer to SFU's policies and procedures on academic integrity,\r\n  http://www.sfu.ca/policies/Students/index.html .\r\nYou can also contact the Office of the Ombudsperson for assistance in navigating University procedures.\r\n"},
                 {"field": "facts",
                  "label": "copied (other knew)",
                  "text": "{{FNAME}} was given a solution to {{ACTIVITIES}} by another student. The other student seems to have completed the work independently. Both students submitted the work as their own."},
                 {"field": "facts",
                  "label": "copied (without knowledge)",
                  "text": "{{FNAME}} copied the work of another student on {{ACTIVITIES}} without his/her knowledge.  Both students submitted the work as their own."},
                 {"field": "meeting_summary",
                  "label": "admitted",
                  "text": "The student admitted academic dishonesty as described below in \u201cfacts of the case\u201d."},
                 {"field": "meeting_summary",
                  "label": "quote email",
                  "text": "The student explained the situation in his/her email:\r\n\r\nbq. PASTE QUOTE HERE"},
                 {"field": "meeting_summary",
                  "label": "explained",
                  "text": "{{FNAME}} explained that..."},
                 ]
    for data in templates:
        t = DisciplineTemplate(**data)
        t.save()

    cmpt = Unit.objects.get(slug='cmpt')
    a = Account(account_number=12345, position_number=12345, title='MSc TA', unit=cmpt)
    a.save()
    a = Account(account_number=12346, position_number=12346, title='PhD TA', unit=cmpt)
    a.save()
    a = Account(account_number=12347, position_number=12347, title='External TA', unit=cmpt)
    a.save()
    a = Account(account_number=12348, position_number=12348, title='Undergrad TA', unit=cmpt)
    a.save()

    uc = UserConfig(user=Person.objects.get(userid='dzhao'), key='advisor-token', value={'token': '30378700c0091f34412ec9a082dca267'})
    uc.save()
    uc = UserConfig(user=Person.objects.get(userid='ggbaker'), key='advisor-token', value={'token': '082dca26730378700c0091f34412ec9a'})
    uc.save()
    p = Person(userid='probadmn', emplid='200002387', first_name='Problem', last_name='Admin')
    p.save()
    uc = UserConfig(user=p, key='problems-token', value={'token': '30378700c0091f34412ec9a082dca268'})
    uc.save()

    p = Person(userid='teachadm', emplid='200002388', first_name='Teaching', last_name='Admin')
    p.save()
    r = Role(person=p, role="TADM", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    #sp = SemesterPlan(semester=Semester.objects.get(name=TEST_SEMESTER), name='Test Plan', unit=Unit.objects.get(slug='cmpt'), slug='test-plan')
    #sp.save()
    #o = PlannedOffering(plan=sp, course=Course.objects.get(slug='cmpt-102'), section='D100', campus='BRNBY', enrl_cap=100)
    #o.save()
    #PlanningCourse.create_for_unit(Unit.objects.get(slug='cmpt'))
    #te = TeachingEquivalent(pk=1, instructor=Person.objects.get(userid='ggbaker'), semester=Semester.objects.get(name=TEST_SEMESTER), credits_numerator=1, credits_denominator=1, summary="Foo", status='UNCO')
    #te.save()
    #ti = TeachingIntention(instructor=Person.objects.get(userid='ggbaker'), semester=Semester.objects.get(name=TEST_SEMESTER), count=2)
    #ti.save()
    #tc = TeachingCapability(instructor=Person.objects.get(userid='ggbaker'), course=Course.objects.get(slug='cmpt-102'), note='foo')
    #tc.save()

    p = Person(userid='classam', emplid='200002389', first_name='Curtis', last_name='Lassam')
    p.save()
    r = Role(person=p, role="TECH", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=p, role="SYSA", unit=Unit.objects.get(slug='cmpt'))
    r.save()

    # create some faculty roles
    members = Member.objects.filter(role='INST', offering__owner__slug='cmpt')
    instr = set(m.person for m in members)
    faculty = random.sample(instr, 10)
    for p in faculty:
        Role.objects.get_or_create(person=p, role='FAC', unit=cmpt)



from onlineforms.models import FormGroup, FormGroupMember, Form, Sheet, Field
def create_form_data():
    unit = Unit.objects.get(slug='cmpt')
    fg = FormGroup(name="Admins", unit=unit)
    fg.save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='ggbaker')).save()
    FormGroupMember(formgroup=fg, person=Person.objects.get(userid='classam')).save()

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
    fld5 = Field(label='Prediction', sheet=s2, fieldtype='RADI', config={ "required": False, 'label': 'Prediction', "help_text":"Do you think it's likely this will be approved?", "choice_1": "Yes", "choice_2": "No", "choice_3": "Huh?"})
    fld5.save()
    s3 = Sheet(form=f2, title="Decision", can_view="ALL")
    s3.save()
    fld5 = Field(label='Decision', sheet=s3, fieldtype='RADI', config={ "required": True, 'label': 'Decision', "help_text":"Do you approve this appeal?", "choice_1": "Yes", "choice_2": "No", "choice_3": "See comments"})
    fld5.save()
    fld6 = Field(label='Comments', sheet=s3, fieldtype='MDTX', config={"min_length": 1, "required": False, "max_length": "1000", 'label': 'Comments', "help_text":'Any additional comments'})
    fld6.save()



def import_semesters():
    return IMPORT_SEMESTERS


def realdata_import():
    for strm in NEEDED_SEMESTERS:
        create_fake_semester(strm)
    Unit.objects.get_or_create(label='UNIV', name='Simon Fraser University')

    print("importing course offerings")
    offerings = import_offerings(import_semesters=import_semesters, create_units=True) # extra_where="ct.subject='CMPT' or ct.subject='ENSC'"
    offerings = list(offerings)
    offerings.sort()

    print("importing course members")
    for o in offerings:
        import_offering_members(o, students=False)
    
    # should now have all the "real" people: fake their emplids
    fake_emplids()

def fakestudent_import():
    print("creating fake classes")
    create_classes()

def fakedata_import():
    print("creating other data")
    create_others()
    create_grads()
    create_grad_templ()
    create_more_data()
    create_form_data()
    create_ta_data()
    create_ra_data()

    print("giving sysadmin permissions")
    p=Person(userid='sysa', first_name='System', last_name='Admin', emplid='000054312')
    p.save()
    Role.objects.get_or_create(person=p, role='SYSA', unit=Unit.objects.get(slug='univ'))


def main():
    realdata_import()
    fakestudent_import()
    fakedata_import()

if __name__ == "__main__":
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError("Don't do that.")
    main()
