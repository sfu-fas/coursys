# importer to create fake data for development
# suggestion execution:
#   rm db.sqlite; ./manage.py migrate && python coredata/devtest_importer.py <emplid>

import os, sys, socket
from django.core.wsgi import get_wsgi_application
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

from django.conf import settings
from django.core import serializers
from coredata.models import Person, Unit, Role, Semester, SemesterWeek, Holiday, CourseOffering, Course, Member, MeetingTime
from coredata.importer import import_semester_info, import_offerings, import_offering_members
from coredata.queries import add_person, SIMSConn, cache_by_args
import itertools, random, string

SEMESTER_CUTOFF = '1100' # semesters with label >= this will be included

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
        n = n + random.choice(string.ascii_lowercase)
    return n


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
    p.save()
    u = Unit(label='UNIV', name='Simon Fraser University')
    u.save()
    r = Role(person=p, role='SYSA', unit=u)
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
    create_units()

    # restore ggbaker's real emplid so import_offerings will match
    p = find_person('ggbaker')
    p.emplid = find_emplid('ggbaker')

    # import a few more people we definitely need later
    find_person('popowich')
    find_person('dixon')
    find_person('dzhao')

    # import a limited set of course offerings
    offerings = import_offerings(import_semesters=import_strms, extra_where=
        "(subject='CMPT' AND (catalog_nbr LIKE '%% 12%%')) "
        "OR (subject='ENSC' AND (catalog_nbr LIKE '%% 10%%')) "
        )
    offerings = list(offerings)
    offerings.sort()

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
        userid = "0uuu%i" % (i)
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
        p.save()

    return itertools.chain(
        SemesterWeek.objects.filter(semester__name__gt=SEMESTER_CUTOFF),
        Holiday.objects.filter(semester__name__gt=SEMESTER_CUTOFF),
        Unit.objects.all(),
        Course.objects.all(),
        CourseOffering.objects.all(),
        Person.objects.exclude(first_name='.').order_by('emplid'), # not "Faculty, ."
        Member.objects.all(),
        MeetingTime.objects.all(),
    )

def create_grades():
    undergrads = list(Person.objects.filter(last_name='Student'))
    grads = list(Person.objects.filter(last_name='Grad'))
    for o in CourseOffering.objects.all():
        # TA
        m = Member(person=random.choice(grads), role='TA', offering=o, credits=0, career='NONS', added_reason='TAC')
        m.config['bu'] = 5
        m.save()

        # students
        for p in random.sample(undergrads, 10):
            m = Member(person=p, role='STUD', offering=o, credits=3, career='UGRD', added_reason='AUTO')
            m.save()

    return itertools.chain(
        Member.objects.filter(role__in=['TA', 'STUD']),
    )


def serialize_result(data_func, filename):
    print "creating %s.json" % (filename)
    objs = data_func()
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open(filename + '.json', 'w')
    fh.write(data)
    fh.close()

def main():
    assert not settings.DISABLE_REPORTING_DB
    assert settings.SIMS_PASSWORD

    serialize_result(create_true_core, 'initial_data')
    serialize_result(create_coredata, 'coredata')
    # use/import no real emplids after this
    serialize_result(create_grades, 'grades')

if __name__ == "__main__":
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError, "Don't do that."
    main()