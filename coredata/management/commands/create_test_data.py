import datetime
import itertools
import random
import string

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand
from coredata.models import Semester, Unit, Person, CourseOffering, Course, GENDER_DESCR, VISA_STATUSES, Member, Role
from courselib.testing import TEST_COURSE_SLUG
from dashboard.models import UserConfig
from grades.models import NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity, Activity
from groups.models import Group, GroupMember
from marking.models import ActivityComponent
from privacy.models import set_privacy_signed, set_privacy_da_signed
from submission.models.code import CodeComponent
from submission.models.pdf import PDFComponent

fake_emplid = 200000001


def create_person(fname, prefname, lname, userid):
    global fake_emplid
    p = Person(first_name=fname, pref_first_name=prefname, last_name=lname, userid=userid)
    p.emplid = fake_emplid
    fake_emplid += 1
    p.save()
    return p


def randname(l):
    """
    Generate a random not-very-name-like string.
    """
    n = random.choice(string.ascii_uppercase)
    for _ in range(l-1):
        n = n + random.choice(string.ascii_lowercase + 'àêïõú')
    return n


class Command(BaseCommand):
    def add_arguments(self, parser):
        #parser.add_argument('app', type=str, help='the app to work in')
        pass

    def create_semesters(self):
        this_yr = datetime.date.today().year
        for yr in range(this_yr - 10, this_yr + 10):
            Semester(name=f'{yr-1900}1', start=datetime.date(yr, 1, 2), end=datetime.date(yr, 4, 25)).save()
            Semester(name=f'{yr-1900}4', start=datetime.date(yr, 5, 2), end=datetime.date(yr, 8, 25)).save()
            Semester(name=f'{yr-1900}7', start=datetime.date(yr, 9, 2), end=datetime.date(yr, 12, 20)).save()

    def create_units(self):
        univ = Unit(label='UNIV', name='Simon Fraser University', parent=None)
        univ.save()
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

    def create_test_offering(self):
        instructor = create_person('Gregorʏ', 'Greg', 'Baker', 'ggbaker')

        test_course = Course(subject='CMPT', number='120', title='Introduction to Computing Science and Programming I')
        test_course.save()
        test_offering = CourseOffering(
            semester=Semester.objects.get(name='1237'), subject='CMPT', number='120', section='D100',
            title='Introduction to Computing Science and Programming I', owner=Unit.objects.get(slug='cmpt'),
            component='LEC', instr_mode='P',
            crse_id=1234, class_nbr=12345, campus='BRNBY',
            enrl_cap=150, enrl_tot=20, wait_tot=0, units=3,
            course=test_course,
        )
        test_offering.save()
        assert test_offering.slug == TEST_COURSE_SLUG, "courselib.testing.TEST_COURSE_SLUG must match the created test_offering"

        other_course = Course(subject='CMPT', number='125', title='Introduction to Computing Science and Programming II')
        other_course.save()
        other_offering = CourseOffering(
            semester=Semester.objects.get(name='1237'), subject='CMPT', number='125', section='D100',
            title='Introduction to Computing Science and Programming II', owner=Unit.objects.get(slug='cmpt'),
            component='LEC', instr_mode='P',
            crse_id=1235, class_nbr=12346, campus='BRNBY',
            enrl_cap=150, enrl_tot=0, wait_tot=0, units=3,
            course=other_course,
        )
        other_offering.save()

        test_offering.set_labtut(True)
        test_offering.set_discussion(True)
        test_offering.set_url("http://www.cs.sfu.ca/")
        test_offering.set_taemail("contact-list@example.com")
        test_offering.save()

        for i in range(20):
            userid = "0aaa%i" % (i)
            fname = randname(8)
            p = random.randint(1, 2)
            if p == 1:
                pref = fname[:4]
            else:
                pref = fname
            p = Person(emplid=300000300 + i, userid=userid, last_name='Student', first_name=fname,
                       middle_name=randname(6), pref_first_name=pref)
            p.save()
            Member(person=p, offering=test_offering, role='STUD').save()

            userid = "0ggg%i" % (i)
            fname = randname(8)
            p = random.randint(1, 2)
            if p == 1:
                pref = fname[:4]
            else:
                pref = fname
            p = Person(emplid=300000500 + i, userid=userid, last_name='Grad', first_name=fname, middle_name=randname(6),
                       pref_first_name=pref)
            p.config['gender'] = random.choice(list(GENDER_DESCR.keys()))
            p.config['gpa'] = round(random.triangular(0.0, 4.33, 2.33), 2)
            p.config['visa'] = random.choice([x for x, _ in VISA_STATUSES])
            p.config['citizen'] = random.choice(('Canadian', 'OtherCountrian'))
            p.save()

        Member(person=instructor, offering=test_offering, role='INST').save()
        Member(person=Person.objects.get(userid='0ggg0'), offering=test_offering, role='TA').save()

        # create example activities
        a1 = NumericActivity(offering=test_offering, name='Assignmenț 1', short_name='A1', status='URLS', position=1,
                        percent=10, max_grade=10, due_date=(test_offering.semester.start + datetime.timedelta(days=60))
                        )
        a1.save()
        NumericActivity(offering=test_offering, name="Assignment 2", short_name="A2", status="URLS",
                        due_date=test_offering.semester.start + datetime.timedelta(days=70), percent=10, group=True,
                        max_grade=20, position=2).save()
        LetterActivity(offering=test_offering, name="Project", short_name="Proj", status="URLS",
                       due_date=test_offering.semester.start + datetime.timedelta(days=80), percent=40, group=True,
                       position=3).save()
        LetterActivity(offering=test_offering, name="Report", short_name="Rep", status="URLS",
                       due_date=test_offering.semester.start + datetime.timedelta(days=81), percent=10, group=False, position=4
                       ).save()
        NumericActivity(offering=test_offering, name="Final Exam", short_name="Exam", status="URLS", due_date=None,
                        percent=30, group=False, max_grade=90, position=5).save()
        total = CalNumericActivity(offering=test_offering, name="Final Percent", short_name="Perc", status="INVI",
                           due_date=None, percent=0, group=False, max_grade=100, formula="[[activitytotal]]", position=6
                           )
        total.save()
        CalLetterActivity(offering=test_offering, name="Letter Grade", short_name="Letter", status="INVI",
                          due_date=None, percent=0, group=False, numeric_activity=total, position=6).save()

        # make A1 submittable and markable
        s = CodeComponent(activity=a1, title="Cöde File", description="The code you're submitting.",
                          allowed=".py,.java")
        s.save()
        s = PDFComponent(activity=a1, title="Report", description="Report on what you did.",
                         specified_filename="report.pdf")
        s.save()

        m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part ➀",
                              description="Part ➀ was done well and seems to work.", position=1, slug='part-1')
        m.save()
        m = ActivityComponent(numeric_activity=a1, max_mark=5, title="Part 2",
                              description="Part 2 was done well and seems to work.", position=2)
        m.save()

        # create some groups
        members = list(Member.objects.filter(offering=test_offering, role='STUD'))
        random.shuffle(members)
        m = members.pop()
        g = Group(name="SomeGroup", courseoffering=test_offering, manager=m)
        g.save()
        for m in [m, members.pop()]:
            gm = GroupMember(group=g, student=m, confirmed=True, activity=Activity.objects.get(slug='a2'))
            gm.save()

        m = members.pop()
        g = Group(name="AnotherGroup", courseoffering=test_offering, manager=m)
        g.save()
        for m in [m, members.pop(), members.pop()]:
            gm = GroupMember(group=g, student=m, confirmed=True, activity=Activity.objects.get(slug='a2'))
            gm.save()
            gm = GroupMember(group=g, student=m, confirmed=True, activity=Activity.objects.get(slug='proj'))
            gm.save()

    def create_admin_data(self):
        admin = create_person('Danyu', 'Danyu', 'Zhao', 'dzhao')
        set_privacy_signed(admin)
        set_privacy_da_signed(admin)
        config = UserConfig(user=admin, key='photo-agreement', value={'agree': True})
        config.save()

        u = Unit.objects.get(slug='cmpt')
        role_expiry = datetime.datetime.today() + datetime.timedelta(days=365*10)
        Role(person=admin, role='ADVS', unit=u, expiry=role_expiry).save()
        Role(person=admin, role='ADMN', unit=u, expiry=role_expiry).save()
        Role(person=admin, role='INV', unit=u, expiry=role_expiry).save()
        Role(person=admin, role='OUTR', unit=u, expiry=role_expiry).save()
        Role(person=admin, role='SPAC', unit=u, expiry=role_expiry).save()

        sysadmin = create_person('Phil', 'Phil', 'Boutrol', 'pba7')
        Role(person=sysadmin, role='SYSA', unit=Unit.objects.get(slug='univ'), expiry=role_expiry).save()
        Role(person=Person.objects.get(userid='ggbaker'), role='SYSA', unit=Unit.objects.get(slug='univ'),
                  expiry=role_expiry).save()

    def dump_fixtures(self, filename, objs):
        data = serializers.serialize("json", objs, sort_keys=True, indent=1)
        fh = open('fixtures/' + filename + '.json', 'w')
        fh.write(data)
        fh.close()

    def handle(self, *args, **options):
        assert settings.DEPLOY_MODE != 'production'
        
        self.create_semesters()
        self.create_units()
        self.create_test_offering()
        self.create_admin_data()

        self.dump_fixtures('basedata', itertools.chain(
            Semester.objects.all(),
            Unit.objects.all(),
            Person.objects.filter(userid='ggbaker'),
        ))
        self.dump_fixtures('coredata', itertools.chain(
            Person.objects.all(),
            Role.objects.all(),
            Course.objects.all(),
            CourseOffering.objects.all(),
            Member.objects.all(),
            Activity.objects.all(),
            NumericActivity.objects.all(),
            LetterActivity.objects.all(),
            CalNumericActivity.objects.all(),
            CalLetterActivity.objects.all(),
        ))

