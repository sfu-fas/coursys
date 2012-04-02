# adapted from coredata/demodata-importer.py
import random, string
from coredata.models import Person, Unit, Semester
from django.core import serializers
from grad import models, forms
from grad.models import GradStudent, GradProgram, GradStatus, Scholarship,\
    OtherFunding, Promise, GradRequirement, CompletedRequirement,\
    ScholarshipType


def randname(l):
    n = random.choice(string.ascii_uppercase)
    for _ in range(l-1):
        n = n + random.choice(string.ascii_lowercase)
    return n

def randdesc(l):
    s = ''
    while len(s) < l:
        s += randname(random.randint(1,int(l*(2.0/3.0))))
    if len(s) > l:
        s = s[:l]
    return s
    

fakes = {}
next_emplid = 100
            
def fake_emplid(emplid=None):
    """
    Return a fake EMPLID for this person
    """
    global next_emplid
    base = 600000000
    
    if emplid != None and emplid in fakes:
        return fakes[emplid]
    
    next_emplid += 1
    fake = base + next_emplid
    fakes[emplid] = fake
    return fake

all_gradprograms = {}
def create_fake_gradprograms():
    u = Unit.objects.get(label='CMPT')
    for i in range(10):
        label='%s%sing' % (randname(4), i)
        gp = GradProgram(
                unit=u,
                label=label)
        gp.save()
        all_gradprograms[label] = gp

randnullbool = lambda:random.choice((False, True, None))
randbool = lambda:random.choice((False, True))

all_students = {}
all_gradstudents = {}
def create_fake_gradstudents():
    """
    Make a bunch of fake grad students so we can test searching
    """
    for i in range(100):
        userid = "1grad%s" % (i)
        print userid
        fname = randname(8)
        lname = "Gradstudent"
        p = Person(emplid=fake_emplid(userid), userid=userid, last_name=lname, first_name=fname, middle_name="", pref_first_name=fname[:4])
        p.gender = random.choice(('M','F','U'))
        p.gpa = random.triangular(0.0, 4.33, 2.33)
        p.save()
        all_students[userid] = p
        
        g = GradStudent(
                person=p,
                program=random.choice(all_gradprograms.values()),
                research_area=randname(8)+'ology',
                campus=random.choice([x for x,_ in models.CAMPUS_CHOICES]),
                is_canadian=randnullbool(),
                application_status=[x for x,_ in models.APPLICATION_STATUS_CHOICES])
        g.save()
        all_gradstudents[userid] = g

all_gradstatuses = []
def create_fake_gradstatuses():
    # currently, the end semester can be after the start semester
    # TODO: fix that. maybe.
    statuses = tuple(x for x,_ in models.STATUS_CHOICES)
    semesters = list(Semester.objects.all())
    for _ in range(200):
        gs = GradStatus(
                student=random.choice(all_gradstudents.values()),
                status=random.choice(statuses),
                start=random.choice(semesters),
                end=random.choice(semesters) if randbool() else None,
                )
        gs.save()
        all_gradstatuses.append(gs)

all_financial_support = []
def create_fake_financial_support():
    semesters = list(Semester.objects.all())
    for _ in range(50):
        s = Scholarship(
                scholarship_type=random.choice(ScholarshipType.objects.all()),
                student=random.choice(all_gradstudents.values()),
                amount=random.triangular(100.0, 20000.0, 5000.0),
                start_semester=random.choice(semesters),
                end_semester=random.choice(semesters),
                )
        s.save()
        all_financial_support.append(s)
    for _ in range(20):
        of = OtherFunding(
                student=random.choice(all_gradstudents.values()),
                semester=random.choice(semesters),
                description=randdesc(60),
                amount=random.triangular(100.0, 20000.0, 5000.0),
                eligible=randbool())
        of.save()
        all_financial_support.append(of)
    for _ in range(40):
        p = Promise(
                student=random.choice(all_gradstudents.values()),
                amount=random.triangular(100.0, 40000.0, 20000.0),
                start_semester=random.choice(semesters),
                end_semester=random.choice(semesters),
                )
        p.save()
        all_financial_support.append(p)

all_completedrequirements = []
def create_fake_completedrequirements():
    semesters = list(Semester.objects.all()) + [None, None]
    for _ in range(200):
        cr = CompletedRequirement(
                requirement=random.choice(GradRequirement.objects.all()),
                student=random.choice(all_gradstudents.values()),
                semester=random.choice(semesters),
                )
        cr.save()
        all_completedrequirements.append(cr)

def to_json():
    return serializers.serialize("json", 
            all_gradprograms.values() + 
            all_students.values() + 
            all_gradstudents.values() +
            all_gradstatuses +
            all_financial_support +
            all_completedrequirements)

def main():
    create_fake_gradprograms()
    create_fake_gradstudents()
    create_fake_gradstatuses()
    create_fake_financial_support()
    create_fake_completedrequirements()
    print to_json()
