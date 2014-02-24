# do the import with fake data for development
# suggestion execution:
#   rm db.sqlite; echo "no" | ./manage.py syncdb && ./manage.py migrate && python coredata/testdata_importer.py

import sys, os
sys.path.append(".")
#sys.path.append("courses")
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'

import random, socket, datetime, itertools
from django.core import serializers
from importer import give_sysadmin, create_semesters, import_offerings, import_offering_members, combine_sections, past_cutoff, update_amaint_userids, fix_emplid
from demodata_importer import fake_emplid, fake_emplids, create_classes, create_fake_semester, create_grads
from demodata_importer import create_grad_templ, create_more_data, create_form_data, create_ta_data, create_ra_data
from coredata.models import Member, Person, CourseOffering, Course, Semester, SemesterWeek, MeetingTime, Role, Unit, CAMPUSES, ComputingAccount
from dashboard.models import UserConfig
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity
from submission.models.base import SubmissionComponent
from submission.models.code import CodeComponent
from submission.models.pdf import PDFComponent
#from planning.models import SemesterPlan, PlannedOffering, PlanningCourse, TeachingEquivalent, TeachingCapability, TeachingIntention
from marking.models import ActivityComponent
from groups.models import Group, GroupMember
from grad.models import GradProgram, GradStudent, GradStatus, LetterTemplate, ScholarshipType, \
        Supervisor, GradRequirement, GradFlag
from grad.forms import possible_supervisor_people
from discipline.models import DisciplineTemplate
from ta.models import CourseDescription, TAPosting, TAApplication, CoursePreference, TAContract, TACourse, TAKEN_CHOICES, EXPER_CHOICES
from ra.models import Account, RAAppointment, Project, SemesterConfig, HIRING_CATEGORY_CHOICES, HIRING_CATEGORY_DISABLED
from onlineforms.models import FormGroup, FormGroupMember, Form, Sheet, Field, FormSubmission, SheetSubmission, FieldSubmission
from courselib.testing import TEST_COURSE_SLUG

FULL_TEST_DATA = TEST_COURSE_SLUG
NEEDED_SEMESTERS = [1111,1114,1117, 1121,1124,1127, 1131,1134,1137, 1141,1144,1147, 1151,1154,1157] # at least two years in past and one in future
TEST_SEMESTER = 1141

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
        if Member.objects.filter(person=p, offering=crs, role="STUD"):
            # randomly added by other student-adder: skip
            continue

        m = Member(person=p, offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO",
                labtut_section=lab)
        m.save()
    
    if not Member.objects.filter(person__userid='ggbaker', offering=crs, role='INST'):
        Member(person=Person.objects.get(userid='ggbaker'), offering=crs, role='INST').save()
    
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
    g = Group(name="SomeGroup", courseoffering=crs, manager=Member.objects.get(offering=crs, person__userid="0aaa0", role='STUD'))
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
    r = Role(person=p, role="GRAD", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    p = Person(emplid=fake_emplid(), first_name="Danyu", last_name="Zhao", pref_first_name="Danyu", userid="dzhao")
    p.save()
    r = Role(person=p, role="ADVS", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=Person.objects.get(userid='dixon'), role="PLAN", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=Person.objects.get(userid='ggbaker'), role="FAC", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=Person.objects.get(userid='dixon'), role="FAC", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=Person.objects.get(userid='diana'), role="FAC", unit=Unit.objects.get(slug='cmpt'))
    r.save()

    p = Person.objects.get(userid='ggbaker')
    r = Role(person=p, role="GRAD", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=p, role="ADMN", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=p, role="TAAD", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=p, role="FUND", unit=Unit.objects.get(slug='cmpt'))
    r.save()
    r = Role(person=Person.objects.get(userid='popowich'), role="GRPD", unit=Unit.objects.get(slug='cmpt'))
    r.save()


def serialize(filename):
    """
    output JSON of everything we created
    """
    objs = itertools.chain(
            Semester.objects.all(),
            SemesterWeek.objects.all(),
            CourseOffering.objects.all(),
            Course.objects.all(),
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
            GradRequirement.objects.all(),
            GradFlag.objects.all(),
            Supervisor.objects.all(),
            ScholarshipType.objects.all(),
            DisciplineTemplate.objects.all(),
            LetterTemplate.objects.all(),
            Account.objects.all(),
            UserConfig.objects.all(),
            #SemesterPlan.objects.all(),
            #PlannedOffering.objects.all(),
            #PlanningCourse.objects.all(),
            #TeachingEquivalent.objects.all(),
            #TeachingIntention.objects.all(),
            #TeachingCapability.objects.all(),
            FormGroup.objects.all(),
            FormGroupMember.objects.all(),
            Form.objects.all(),
            Sheet.objects.all(),
            Field.objects.all(),
            FormSubmission.objects.all(),
            SheetSubmission.objects.all(),
            FieldSubmission.objects.all(),
            TAPosting.objects.all(),
            TAApplication.objects.all(),
            CoursePreference.objects.all(),
            CourseDescription.objects.all(),
            TAContract.objects.all(),
            TACourse.objects.all(),
            RAAppointment.objects.all(),
            Project.objects.all(),
            SemesterConfig.objects.all(),
            )
    
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open(filename, "w")
    fh.write(data)
    fh.close()

def import_semesters():
    """
    What semesters should we actually import? (returns tuple of strm values)
    """
    sems = Semester.objects.filter(end__gte=past_cutoff)
    return tuple(s.name for s in sems)

def create_units():
    univ = Unit.objects.get(label='UNIV')
    fas = Unit(label='FAS', name='Faculty of Applied Sciences', parent=univ).save()
    ensc = Unit(label='ENSC', name='School of Engineering Science', parent=fas, acad_org='ENG SCI').save()
    cmpt = Unit(label='CMPT', name='School of Computing Science', parent=fas, acad_org='COMP SCI')
    cmpt.set_address(['9971 Applied Sciences Building', '8888 University Drive, Burnaby, BC', 'Canada V5A 1S6'])
    cmpt.set_email('csdept@sfu.ca')
    cmpt.set_web('http://www.cs.sfu.ca/')
    cmpt.set_tel('778-782-4277')
    cmpt.set_fax('778-782-3045')
    cmpt.set_informal_name('Computing Science')
    cmpt.config['sessional_pay'] = 10000
    cmpt.set_deptid('12345')
    cmpt.save()

def main():
    for strm in NEEDED_SEMESTERS:
        create_fake_semester(strm)
    create_units()

    print "getting emplid/userid mapping"
    update_amaint_userids()

    print "importing course offerings"
    # get very few courses here so there isn't excess data hanging around
    offerings = import_offerings(import_semesters=import_semesters, create_units=True, extra_where=
        #"(subject='CMPT' AND (catalog_nbr LIKE '%%165%%')) "
        #"OR (subject='ENSC' AND (catalog_nbr LIKE '%% 100%%')) "
        "(subject='CMPT' AND (catalog_nbr LIKE '%% 1%%' OR catalog_nbr LIKE '%% 2%%')) "
        "OR (subject='ENSC' AND (catalog_nbr LIKE '%% 2_5%%')) "
        )
    offerings = list(offerings)
    offerings.sort()
    
    print "importing course members"
    for o in offerings:
        import_offering_members(o, students=False)

    # should now have all the "real" people: fake their emplids
    fake_emplids()
    ComputingAccount.objects.all().delete()

    # make sure these people are here, since we need them
    if not Person.objects.filter(userid='ggbaker'):
        Person(userid='ggbaker', first_name='Gregory', last_name='Baker', emplid='000001233').save()
    if not Person.objects.filter(userid='dixon'):
        Person(userid='dixon', first_name='Tony', last_name='Dixon', emplid='000001234').save()
    if not Person.objects.filter(userid='diana'):
        Person(userid='diana', first_name='Diana', last_name='Cukierman', emplid='000001235').save()
    if not Person.objects.filter(userid='popowich'):
        Person(userid='popowich', first_name='Fred', last_name='Popowich', emplid='000001236').save()

    print "creating fake classess"
    create_classes()
    create_test_classes()


    print "creating other data"
    create_others()
    create_grad_templ()
    create_more_data()
    create_form_data()
    combine_sections(get_combined())
    
    print "creating grad students"
    create_grads()
    create_ta_data()
    create_ra_data()

    print "giving sysadmin permissions"
    give_sysadmin(['ggbaker', 'sumo'])
    
    serialize("new-test.json")




if __name__ == "__main__":
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError, "Don't do that."
    main()

