# do the import with fake data for development

from importer import *

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

# http://www.fakenamegenerator.com/
# TODO: Unicode, grad students (also TAs), same names
students = [  # userid,last,middle,first,preffirst, courses
    ['0kvm', 'Moore', 'Veronica', 'Kimberly', 'Kim',
        [('1097-cmpt-165-d100', 'UGRD', 3), ('1097-cmpt-165-d103', 'UGRD', 0),
         ('1097-cmpt-120-d100', 'UGRD', 3), ('1097-cmpt-120-d102', 'UGRD', 0),
         ('1101-cmpt-125-d200', 'UGRD', 3), ('1101-cmpt-125-d203', 'UGRD', 0),
         ('1101-cmpt-212-d100', 'UGRD', 3)]],
    ['0changh', 'Han', '', 'Chang', 'Chang', [('1101-cmpt-426-d100', 'UGRD', 3)]],
    ['0rjl23', 'Larkin', 'Jane', 'Rebecca', 'Becky', [('1101-cmpt-426-d100', 'UGRD', 3), ('1101-cmpt-475-e100', 'UGRD', 3)]],
    ['0sta1234', "Tang", '', 'Shaiming', 'Steven', [('1097-cmpt-300-d100','UGRD',3), ('1097-cmpt-322w-d100','UGRD',3), ('1097-cmpt-371-d100','UGRD',3), ('1101-cmpt-371-d100','UGRD',3), ('1101-cmpt-441-d100','UGRD',3)]],
    ['0kel', 'Kelowna', 'J', 'Robert', 'Bob', [('1097-cmpt-xx1-a100','UGRD',3)]],
    ['0grad', 'Gradstudent', '', 'Douglas', 'Doug', [('1101-cmpt-711-g100','GRAD',3), ('1101-cmpt-880-g100','GRAD',3)]],
    #['0', '', '', '', '', [(,,)]],
    #['0', '', '', '', '', [(,,)]],
    ]

# put a bunch of students in CMPT 165
for i in range(20):
    if i%2 == 0:
        crs = [('1101-cmpt-165-d100', 'UGRD', 3), ('1101-cmpt-165-d101', 'UGRD', 0)]
    else:
        crs = [('1101-cmpt-165-d100', 'UGRD', 3), ('1101-cmpt-165-d102', 'UGRD', 0)]

    students.append( ['0aaa'+str(i), "Student", "Q", chr(65+i), chr(65+i), crs] )

# put a bunch of students in CMPT 120
for i in range(20):
    crs = [('1101-cmpt-120-d100', 'UGRD', 3), ('1101-cmpt-120-d107', 'UGRD', 0)]
    # ... and half of them in MACM 101
    if i%2 == 0:
        crs.append(('1101-macm-101-d100', 'UGRD', 3))
    students.append( ['0bbb'+str(i), "Student", "X", chr(65+i)+chr(97+i), chr(65+i)+chr(97+i), crs] )


def create_students():
    """
    import fake students
    """
    for userid,last,middle,first,preffirst,courses in students:
        u = Person.objects.filter(userid=userid)
        if len(u)>0:
            continue
        
        p = Person(emplid=fake_emplid(), userid=userid, last_name=last, first_name=first, middle_name=middle, pref_first_name=preffirst)
        p.save()
        
        for slug, career, credits in courses:
            c = CourseOffering.objects.get(slug=slug)
            m = Member(person=p, offering=c, role='STUD', credits=credits, career=career, added_reason="AUTO")
            m.save()
            
def create_tas():
    """
    import fake TAs
    """
    p = Person.objects.get(userid="0grad")
    c = CourseOffering.objects.get(slug='1101-cmpt-165-d100')
    m = Member(person=p, offering=c, role='TA', credits=0, career='NONS', added_reason="AUTO")
    m.save()


def main(passwd=None):
    if passwd == None:
        raise NotImplementedError, "TODO: web form input"
    
    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=passwd, db=import_name, port=import_port)
    db = dbconn.cursor()
    
    # Drop everybody (and re-add later if they're still around)
    Member.objects.filter(added_reason="AUTO").update(role="DROP")
    
    # People to fetch: manually-added members of courses (and everybody else we find later)
    members = [(m.person.emplid, m.offering) for m in Member.objects.exclude(added_reason="AUTO")]
    
    print "importing course offerings"
    import_offerings(db)
    print "importing meeting times"
    #import_meeting_times(db)
    print "importing instructors"
    members += import_instructors(db)
    
    print "importing personal info"
    import_people(db, members)
    fake_emplids()
    
    print "importing fake students"
    create_students()
    create_tas()
    
    
    


if __name__ == "__main__":
    import getpass
    passwd = getpass.getpass('Database password: ')
    main(passwd)
