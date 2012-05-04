# do the import with fake data for development
# suggestion execution:
#   rm db.sqlite; echo "no" | ./manage.py syncdb && ./manage.py migrate && python coredata/testdata_importer.py

import random, socket, datetime, itertools
from django.core import serializers
from importer import give_sysadmin, create_semesters, import_offerings, import_offering_members, combine_sections
from demodata_importer import fake_emplid, fake_emplids, create_classes
from coredata.models import Member, Person, CourseOffering, Semester, SemesterWeek, MeetingTime, Role, Unit, CAMPUSES
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity
from submission.models.base import SubmissionComponent
from submission.models.code import CodeComponent
from submission.models.pdf import PDFComponent
from marking.models import ActivityComponent
from groups.models import Group, GroupMember
from grad.models import GradProgram, GradStudent, GradStatus
from discipline.models import DisciplineTemplate

FULL_TEST_DATA = "2012su-cmpt-383-d1"

def get_combined():
    combined_sections = [
        ]
    return combined_sections


def test_class_1(slug):
    """
    main test course: 20 students, TA, some assignments
    """
    crs = CourseOffering.objects.get(slug=slug)
    
    crs.set_labtut(True)
    crs.set_url("http://www.cs.sfu.ca/CC/165/common/")
    crs.set_taemail("cmpt-165-contact@sfu.ca")
    crs.save()
    for i in range(20):
        lab = "D1%02i" % (random.randint(1,4))
        p = Person.objects.get(userid="0aaa%i"%(i))
        m = Member(person=p, offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO",
                labtut_section=lab)
        m.save()
    
    # create a TA
    p = Person(emplid=fake_emplid(), userid="0grad1", last_name="Gradstudent", first_name="Douglas", middle_name="", pref_first_name="Doug")
    p.save()
    m = Member(person=p, offering=crs, role="TA", credits=0, career="NONS", added_reason="AUTO",
            labtut_section=None)
    m.save()
    
    
    # create example activities
    crs.activity_set.all().update(deleted=True)
    a1 = NumericActivity(offering=crs, name="Assignment 1", short_name="A1", status="RLS",
        due_date=crs.semester.start + datetime.timedelta(days=60), percent=10, group=False,
        max_grade=10, position=1)
    a1.set_url("http://www.cs.sfu.ca/CC/165/common/a1")
    a1.save()
    a2 = NumericActivity(offering=crs, name="Assignment 2", short_name="A2", status="URLS",
        due_date=crs.semester.start + datetime.timedelta(days=70), percent=10, group=True,
        max_grade=20, position=2)
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
    s = CodeComponent(activity=a1, title="Code File", description="The code you're submitting.",
        allowed=".py,.java")
    s.save()
    s = PDFComponent(activity=a1, title="Report", description="Report on what you did.",
        specified_filename="report.pdf")
    s.save()
    
    m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part 1", description="Part 1 was done well and seems to work.", position=1)
    m.save()
    m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part 2", description="Part 2 was done well and seems to work.", position=2)
    m.save()
    
    # create some groups
    g = Group(name="SomeGroup", courseoffering=crs, manager=Member.objects.get(offering=crs, person__userid="0aaa0"))
    g.save()
    for userid in ['0aaa0', '0aaa1', '0aaa5', '0aaa10']:
        gm = GroupMember(group=g, student=Member.objects.get(offering=crs, person__userid=userid), confirmed=True, activity=a2)
        gm.save()
    
    g = Group(name="AnotherGroup", courseoffering=crs, manager=Member.objects.get(offering=crs, person__userid="0aaa4"))
    g.save()
    for userid in ['0aaa4', '0aaa6', '0aaa7', '0aaa14']:
        gm = GroupMember(group=g, student=Member.objects.get(offering=crs, person__userid=userid), confirmed=True, activity=a2)
        gm.save()
        gm = GroupMember(group=g, student=Member.objects.get(offering=crs, person__userid=userid), confirmed=True, activity=pr)
        gm.save()



def create_test_classes():
    # full test data for this course
    test_class_1(FULL_TEST_DATA)
    # minimal test data for this course
    #test_class_2(MIN_TEST_DATA)


def create_others():
    """
    Create other users for the test data set
    """
    p = Person(emplid=fake_emplid(), first_name="Susan", last_name="Kindersley", pref_first_name="sumo", userid="sumo")
    p.save()
    r = Role(person=p, role="GRAD", unit=Unit.objects.get(slug='comp'))
    r.save()
    p = Person(emplid=fake_emplid(), first_name="Danyu", last_name="Zhao", pref_first_name="Danyu", userid="dzhao")
    p.save()
    r = Role(person=p, role="ADVS", unit=Unit.objects.get(slug='comp'))
    r.save()

def create_grads():
    """
    Put the grad students created before into GradStudent records.
    """
    gp = GradProgram(unit=Unit.objects.get(slug='comp'), label='MSc Project', description='MSc Project option')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='comp'), label='MSc Thesis', description='MSc Thesis option')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='comp'), label='PhD', description='PhD')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='eng'), label='MEng', description='Masters in Engineering')
    gp.save()
    gp = GradProgram(unit=Unit.objects.get(slug='eng'), label='PhD', description='PhD')
    gp.save()
    programs = list(GradProgram.objects.all())
    for p in Person.objects.filter(userid__endswith='grad'):
        gp = random.choice(programs)
        campus = random.choice(list(CAMPUSES))
        appst = random.choice(['CONF', 'CONF', 'CONF', 'CONF', 'REJE', 'DECL'])
        gs = GradStudent(person=p, program=gp, campus=campus, application_status=appst)
        gs.save()

        startsem = random.choice(list(Semester.objects.filter(name__lt=Semester.current().name)))
        st = GradStatus(student=gs, status='APPL', start=startsem)
        st.save()
        st = GradStatus(student=gs, status=random.choice(['ACTI', 'ACTI', 'LEAV']), start=startsem.next_semester())
        st.save()
        if random.random() > 0.5:
            st = GradStatus(student=gs, status=random.choice(['GRAD', 'GRAD', 'WIDR']), start=startsem.next_semester().next_semester().next_semester())
            st.save()
        
        # TODO: supervisors, completed requirements, letter templates and letters 


def create_discipline_templ():
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
                  "text": u"The student admitted academic dishonesty as described below in \u201cfacts of the case\u201d."},
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


def serialize(filename):
    """
    output JSON of everything we created
    """
    objs = itertools.chain(
            Semester.objects.all(),
            SemesterWeek.objects.all(),
            CourseOffering.objects.all(),
            MeetingTime.objects.all(),
            Person.objects.all(),
            Member.objects.all(),
            Activity.objects.all(),
            NumericActivity.objects.all(),
            LetterActivity.objects.all(),
            CalNumericActivity.objects.all(),
            CalLetterActivity.objects.all(),
            SubmissionComponent.objects.all(),
            CodeComponent.objects.all(),
            PDFComponent.objects.all(),
            ActivityComponent.objects.all(),
            Group.objects.all(),
            GroupMember.objects.all(),
            Role.objects.all(),
            Unit.objects.all(),
            GradProgram.objects.all(),
            GradStudent.objects.all(),
            GradStatus.objects.all(),
            DisciplineTemplate.objects.all(),
            )
    
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open(filename, "w")
    fh.write(data)
    fh.close()


def main():
    create_semesters()
    
    print "importing course offerings"
    # get very few courses here so there isn't excess data hanging around
    offerings = import_offerings(extra_where=
        "(subject='CMPT' AND (catalog_nbr LIKE '%% 383%%' OR catalog_nbr LIKE '%% 47%%')) "
        "OR (subject='ENSC' AND (catalog_nbr LIKE '%% 2_5%%')) "
        )
    offerings = list(offerings)
    offerings.sort()
    
    print "importing course members"
    for o in offerings:
        import_offering_members(o, students=False)
    
    # should now have all the "real" people: fake their emplids
    fake_emplids()
    
    print "creating fake classess"
    create_classes()
    create_test_classes()
    create_others()
    create_discipline_templ()
    combine_sections(get_combined())
    
    print "creating grad students"
    create_grads()

    print "giving sysadmin permissions"
    #give_sysadmin(['ggbaker', 'sumo'])
    give_sysadmin(['sumo'])
    
    serialize("new-test.json")


if __name__ == "__main__":
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError, "Don't do that."
    main()
