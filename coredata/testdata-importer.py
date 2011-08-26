# do the import with fake data for development
# suggestion execution:
#   rm db.sqlite; echo "no" | ./manage.py syncdb; ./manage.py migrate; echo "dbpassword" | python coredata/testdata-importer.py

import MySQLdb, random, string, socket, datetime, itertools
from django.core import serializers
from importer import import_host, import_name, import_user, import_port
from importer import give_sysadmin, create_semesters, import_offerings, import_instructors, import_meeting_times
from coredata.models import Member, Person, CourseOffering, Semester, SemesterWeek, MeetingTime, Role
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity
from submission.models.base import SubmissionComponent
from submission.models.code import CodeComponent
from submission.models.pdf import PDFComponent
from marking.models import ActivityComponent
from groups.models import Group, GroupMember

FIRSTTERM = "1111"
DATA_WHERE = '(subject="CMPT" or subject="MACM") and strm>="'+FIRSTTERM+'"'
FULL_TEST_DATA = "1114-cmpt-120-d100"
MIN_TEST_DATA = "1114-cmpt-165-c100"

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
    for i in range(l-1):
        n = n + random.choice(string.ascii_lowercase)
    return n


def test_class_1(slug):
    """
    main test course: 40 students, TA, some assignments
    """
    crs = CourseOffering.objects.get(slug=slug)
    
    crs.set_labtut(True)
    crs.set_url("http://www.cs.sfu.ca/CC/165/common/")
    crs.set_taemail("cmpt-165-contact@sfu.ca")
    crs.save()
    for i in range(40):
        lab = "D1%02i" % (random.randint(1,4))
        fname = randname(8)
        p = Person(emplid=fake_emplid(), userid="0aaa%i"%(i), last_name="Student", first_name=fname, middle_name="", pref_first_name=fname[:4])
        p.save()
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
    
def test_class_2(slug):
    """
    another test course with jsut some student and no other config
    """
    crs = CourseOffering.objects.get(slug=slug)
    for i in range(40):
        lab = "D1%02i" % (random.randint(1,4))
        fname = randname(8)
        p = Person(emplid=fake_emplid(), userid="0bbb%i"%(i), last_name="Student", first_name=fname, middle_name="", pref_first_name=fname[:4])
        p.save()
        m = Member(person=p, offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO",
                labtut_section=lab)
        m.save()


def create_classes():
    # full test data for this course
    test_class_1(FULL_TEST_DATA)
    # minimal test data for this course
    test_class_2(MIN_TEST_DATA)


def import_offering(db, offering):
    """
    Import all data for the course: instructors meeting times.
    """
    # drop all automatically-added members: will be re-added later on import
    Member.objects.filter(added_reason="AUTO", offering=offering).update(role='DROP')
    
    import_instructors(db, offering)
    import_meeting_times(db, offering)

def create_others():
    """
    Create other users for the test data set
    """
    p = Person(emplid=fake_emplid(), first_name="Susan", last_name="Kindersley", pref_first_name="sumo", userid="sumo")
    p.save()
    p = Person(emplid=fake_emplid(), first_name="Danyu", last_name="Zhao", pref_first_name="Danyu", userid="dzhao")
    p.save()
    r = Role(person=p, role="ADVS", department="CMPT")
    r.save()


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
            )
    
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open(filename, "w")
    fh.write(data)
    fh.close()


def main(passwd):
    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=passwd, db=import_name, port=import_port)
    db = dbconn.cursor()
    print "importing course offerings"
    offerings = import_offerings(db, DATA_WHERE)
    
    for o in offerings:
        import_offering(db, o)
    
    # should now have all the "real" people: fake their emplids
    fake_emplids()
    
    print "creating fake classess"
    create_classes()
    
    create_others()

    print "giving sysadmin permissions"
    give_sysadmin(['ggbaker', 'sumo'])
    
    serialize("new-test.json")


if __name__ == "__main__":
    passwd = raw_input()
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError, "Don't do that."
    main(passwd)
