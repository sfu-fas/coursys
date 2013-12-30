import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Max
from coredata.queries import DBConn, get_names, get_or_create_semester, add_person, get_person_by_userid
from coredata.models import Person, Semester, Unit, CourseOffering, Course, SemesterWeek
from grad.models import GradProgram, GradStudent, GradRequirement, CompletedRequirement, Supervisor, GradStatus, \
        Letter, LetterTemplate, Promise, Scholarship, ScholarshipType, OtherFunding, GradProgramHistory, GradFlag, \
        FinancialComment
from ta.models import TAContract, TAApplication, TAPosting, TACourse, CoursePreference, SkillLevel, Skill, CourseDescription, CampusPreference
from ra.models import RAAppointment, Account, Project
from coredata.importer import AMAINTConn, get_person, get_person_grad, import_one_offering, import_instructors, update_amaint_userids
import datetime, json, time, decimal

from cortez_import import CortezConn

class TAImport(object):
    IMPORT_USER = 'csilop'
    UNIT = Unit.objects.get(slug='cmpt')
    TA_CONTACT = Person.objects.get(userid='ggbaker')
    
    CATEGORY_MAP = {
                    'mscc': 'GTA1',
                    'mscp': 'GTA1',
                    'msct': 'GTA1',
                    'msc': 'GTA1',
                    'phd': 'GTA2',
                    'bsc': 'UTA',
                    'ext': 'ETA',
                    '': 'ETA',
                    }
    INITIAL_MAP = {
                   'yes': 'INIT',
                   None: 'INIT',
                   'no': 'REAP',
                   }
    TA_DESC_MAP = {
                   'Office/Marking': 'Office/Marking',
                   'Office/Marking/Labs': 'Office/Marking/Labs',
                   'Development': 'Open Lab',
                   'CMPT': 'Open Lab',
                   'ARC': 'Open Lab',
                   'MTF': 'Open Lab',
                   'Course': 'Open Lab',
                   'course': 'Open Lab',
                   }
    CATEGORY_INDEX = {'GTA1': 0, 'GTA2': 1, 'UTA': 2, 'ETA': 3}
    # skill level words -> values
    SKILL_LEVEL_MAP = {
                       'None': 'NONE',
                       None: 'NONE',
                       '': 'NONE',
                       'Some': 'SOME',
                       'Expert': 'EXPR',
                       }
    CAMPUS_PREF_MAP = {
                       'B': ('BRNBY', 'PRF'),
                       'b': ('BRNBY', 'WIL'),
                       'S': ('SURRY', 'PRF'),
                       's': ('SURRY', 'WIL'),
                       'H': ('VANCR', 'PRF'),
                       'h': ('VANCR', 'WIL'),
                       }
    
    def __init__(self):
        self.db = CortezConn()
        self.db.execute("USE [esp]", ())

    def setup_accounts(self):
        accounts = [
                    ('00691', '11', 'MSc TA'),
                    ('06406', '11', 'PhD TA'),
                    ('06407', '11', 'External TA'),
                    ('99622', '11', 'Undergrad TA'),
                    ('00690', '11', 'Undergrad TA'),
                    ]
        self.positions = {}
        for p, a, desc in accounts:
            acc, _ = Account.objects.get_or_create(unit=self.UNIT, position_number=p, account_number=a)
            acc.title = desc
            acc.save()
            self.positions[p] = acc.id

    def make_fake_offering(self, sem, subject, number, section, title):
        """
        Create a fake offering for the old open lab/development courses
        """
        o = CourseOffering(subject=subject, number=number, section=section+'00', semester=Semester.objects.get(name=sem),
                           component='OPL', owner=self.UNIT, title=title, enrl_tot=0, enrl_cap=0, wait_tot=0)
        o.save()
        return o
    
    def get_offering_map(self):
        print "Mapping cortez offerings to CourSys..."
        # try the cache first: this is slow to build.
        try:
            fp = open("offering_map_cache.json", 'r')
            offeringid_map = json.load(fp)
            offeringid_map = dict([(k, CourseOffering.objects.get(id=offeringid_map[k])) for k in offeringid_map])
            self.offeringid_map = offeringid_map
            fp.close()
            print "Using cached offering map."
            return
        except IOError:
            pass
        
        offeringid_map = {}
        self.db.execute("SELECT Offering_ID, Semester_Description, Course_Number, Section, o.hasLabs, c.Course_Title "
                        "FROM Offerings o, Resource_Semesters s, Courses c "
                        "WHERE o.Semester_ID=s.Semester_ID AND o.Course_ID=c.Course_ID "
                        "ORDER BY Semester_Description", ())
        last = None
        for off_id, semname, crsnumber, section, hasLabs, title in self.db:
            if semname != last:
                print semname
                last = semname
            subject, number = crsnumber.split()
            
            # clean up ugliness from cortez
            if section[0]=='D' and number[0]>'4':
                section = 'G' + section[1:]

            if number.startswith('00'):
                number = 'XX' + number[2:]
            elif number.startswith('0'):
                number = 'X' + number[1:]
            elif number == '---':
                number = 'XXX'
            
            if semname in ['0987', '0991', '0994', '0997'] and subject=='CMPT' and number=='165':
                # was offered as CMPT 118 then
                number = '118'
            
            offerings = CourseOffering.objects.filter(subject=subject, number__startswith=number, semester__name=semname, section__startswith=section, section__endswith='00')
            if offerings.count() > 1:
                raise ValueError, "multiple offerings found: " + str(offerings)
            elif offerings:
                o = offerings[0]
                offeringid_map[off_id] = o
                o.set_labtas(bool(hasLabs))
                o.save()
            else:
                get_or_create_semester(semname)
                o = import_one_offering(semname, subject, number, section+'00')
                if o is None:
                    if number in ['XXX', 'XX0', 'XX2']:
                        o = self.make_fake_offering(semname, subject, number, section, title)        
                        offeringid_map[off_id] = o            
                    else:
                        print "Can't find:", semname, subject, number, section
                        continue
                else:
                    offeringid_map[off_id] = o
                    o.set_labtas(bool(hasLabs))
                    o.save()
            
            # get instructors if we can: might as well have better data
            #if o.crse_id and o.class_nbr:
            #    import_instructors(o)
        
        self.offeringid_map = offeringid_map
        
        # drop in a file to cache over multiple runs
        fp = open("offering_map_cache.json", 'w')
        # convert offerings to offering.ids for JSON
        offeringid_map = dict([(k, offeringid_map[k].id) for k in offeringid_map])
        json.dump(offeringid_map, fp, indent=1)
        fp.close()
    
    @transaction.atomic
    def get_ta_postings(self):
        print "Getting TA semester postings..."
        self.setup_accounts()
        self.db.execute("SELECT currentYear, currentSem, applicationdeadline, acceptdeadline, "
                        "gta1amount, gta2amount, etaamount, utaamount, "
                        "gta1scholarship, gta2scholarship, etascholarship, utascholarship, "
                        "gta1positionNum, gta2positionNum, etapositionNum, utapositionNum, "
                        "asdday, asdmonth, asdYear, "
                        "aedday, aedmonth, aedYear "
                        "FROM tasearch.dbo.semesterinfo", ())
        for year, sem, applic, accept, gta1a,gta2a,etaa,utaa, gta1s,gta2s,etas,utas, gta1p,gta2p,etap,utap, asd,asm,asy, aed,aem,aey in self.db:
            strm = year+sem
            salary = [gta1a,gta2a,utaa,etaa]
            schol = [gta1s,gta2s,utas,etas]
            positions = [self.positions[p] for p in [gta1p,gta2p,utap,etap]]
            
            # fix broken data in system
            if asy < 1900: asy += 2000
            if aey < 1900: aey += 2000
            if strm in ['1107']:
                asm, asd = asd, asm
                aem, aed = aed, aem
            if strm in ['1111']:
                asm = 1

            start = datetime.date(asy, asm, asd)
            end = datetime.date(aey, aem, aed)
            try:
                applic = datetime.datetime.strptime(applic, "%B %d, %Y").date()
            except ValueError:
                applic = start
            try:
                accept = datetime.datetime.strptime(accept, "%B %d, %Y").date()
            except ValueError:
                accept = start

            semester = get_or_create_semester(strm)
            semester.save()
            postings = TAPosting.objects.filter(unit=self.UNIT, semester=semester)
            if postings:
                posting = postings[0]
            else:
                posting = TAPosting(unit=self.UNIT, semester=semester)

            posting.opens = applic
            posting.closes = applic
            posting.config['salary'] = salary
            posting.config['scholarship'] = schol
            posting.config['start'] = start
            posting.config['end'] = end
            posting.config['deadline'] = accept
            posting.config['contact'] = self.TA_CONTACT.id
            posting.config['accounts'] = positions
            posting.config['payperiods'] = "%.1f" % (self.total_seconds(end-start)/3600/24/14,) # close enough for the import
            posting.save()
    
    def create_fake_posting(self, sem):
        "Create totally fake posting object: better than throwing away corresponding TAs"
        print "  Faking TAPosting for %s" % (sem)
        posting = TAPosting(unit=self.UNIT, semester=sem)
        posting.opens = sem.start
        posting.closes = sem.start
        posting.config['start'] = sem.start
        posting.config['end'] = sem.end
        posting.config['deadline'] = sem.start
        posting.config['contact'] = self.TA_CONTACT.id
        posting.config['payperiods'] = "%.1f" % (self.total_seconds(sem.end-sem.start)/3600/24/14,) # close enough for the import
        posting.save()
        return posting
    
    def total_seconds(self, td):
        """
        Compensate for timedelta.total_seconds not existing in Python 2.6
        """
        tsec = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6)/10**6
        return tsec

    @transaction.atomic
    def get_ta(self, off_id, bu, salary, schol, description, payst, payen, posnum, initial, cond,
               tssu, remarks, app_bu, emplid, cat, sin, status, appid, campuspref):
        """
        Process one TA
        
        Argument order must be the same as query in get_tas below.
        """
        if bu == 0:
            return
        if not(emplid.isdigit() and len(emplid)==9):
            # there's only one, from 2004. Ignore.
            return
        if off_id not in self.offeringid_map:
            # Where did these offerings go? I'm troubled.
            print "missing offering_id:", off_id
            return
        offering = self.offeringid_map[off_id]
        p = get_person(emplid, commit=True)
        
        posting = TAPosting.objects.get(unit=self.UNIT, semester=offering.semester)
        
        # create TAApplication
        apps = TAApplication.objects.filter(posting=posting, person=p)
        app = apps[0]
        
        # create TAContract
        contracts = TAContract.objects.filter(posting=posting, application=app)
        contract = contracts[0]

        # distinct values are ['waitlist', 'accepted', None]; most are None
        contract.status = 'CAN' if status=='waitlist' else 'SGN'
        contract.save()

        

    
    def get_tas(self):  
        self.get_ta_postings()
        self.get_offering_map()
        print "Importing TAs..."
        
        #self.db.execute("SELECT studNum, appYear, appSemester, count(studNum) FROM tasearch.dbo.tainfo i "
        #                "group by studNum, appYear, appSemester having count(studNum)>1 order by appYear", ())
        #print list(self.db) 

        self.db.execute("SELECT o.Offering_ID, o.bu, o.salary, o.scholarship, o.description, "
                        "o.PayrollStartDate, o.PayrollEndDate, o.PositionNumber, o.initAppointment, "
                        "o.conditional, o.tssu, o.remarks, i.base, "
                        "i.studNum, i.category, i.socialInsurance, i.status, i.appId, i.campusPref, i.appYear "
                        "FROM TAOffering o, tasearch.dbo.tainfo i "
                        "WHERE o.TA_ID=i.appId ORDER BY i.appYear", ()) # and i.appYear>'109' 
        initial = None
        for row in list(self.db):
            i = row[-1]
            if i != initial:
                print "  ", 1900+int(i)
                initial = i
                time.sleep(0.5)

            self.get_ta(*row[:-1])

if __name__ == '__main__':
    TAImport().get_tas()


