import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.db import transaction
from django.db.utils import IntegrityError
from coredata.queries import DBConn, get_names, get_or_create_semester
from coredata.models import Person, Semester, Unit, CourseOffering
from grad.models import GradProgram, GradStudent, GradRequirement, CompletedRequirement, Supervisor, GradStatus
from ta.models import TAContract, TAApplication, TAPosting, TACourse
from ta.models import Account
from coredata.importer_rodb import get_person, get_person_grad, import_one_offering
import datetime, json, time

import pymssql, MySQLdb

# in /etc/freetds/freetds.conf: [http://www.freetds.org/userguide/choosingtdsprotocol.htm]
# [global]
#    tds version = 7.0

class CortezConn(DBConn):
    db_host = '127.0.0.1'
    db_user = "fas.sfu.ca\\ggbaker"
    db_name = "ra"
    def escape_arg(self, a):
        return "'" + MySQLdb.escape_string(str(a)) + "'"
    def prep_value(self, v):
        if isinstance(v, basestring):
            return v.strip()
        else:
            return v

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        _ = passfile.next()
        _ = passfile.next()
        pw = passfile.next().strip()

        conn = pymssql.connect(host=self.db_host, user=self.db_user,
             password=pw, database=self.db_name)
        return conn, conn.cursor()

class Introspection(object):
    def table_columns(self, dbname, table):
        db = CortezConn()
        db.execute("USE ["+dbname+"]", ())
        db.execute("select column_name, data_type, is_nullable, character_maximum_length from information_schema.columns where table_name=%s order by ordinal_position", (table,))
        return list(db)
    
    def table_rows(self, dbname, table):
        db = CortezConn()
        db.execute("USE ["+dbname+"]", ())
        db.execute("SELECT * FROM ["+table+"]", ())
        return list(db)
    
    def row_count(self, dbname, table):
        db = CortezConn()
        db.execute("USE ["+dbname+"]", ())
        db.execute("SELECT count(*) FROM ["+table+"]", ())
        return db.fetchone()[0]
    
    def tables(self, dbname):
        db = CortezConn()
        db.execute("USE ["+dbname+"]", ())
        db.execute("SELECT name FROM sysobjects WHERE xtype='U'", ())
        return [n for n, in db]
    
    def databases(self):
        db = CortezConn()
        db.execute("SELECT name FROM master..sysdatabases", ())
        return [n for n, in db]
    
    def print_schema(self):
        for d in self.databases():
            if d in ('model', 'personnel', 'news', 'csguest', 'search', 'space', 'chingtai', 'CE8', 'expenses'):
                # no access
                continue
            if d in ('master', 'msdb', 'pubs', 'faculty'):
                # can't introspect for some reason
                continue
            print
            print "-" * 100
            for t in self.tables(d):
                if (d,t) in (('grad','10_ALL_INFO_FIX'), ('grad', 'PCSdownload'), ('grad', '0_EXCEL_FILE_FIX'),
                             ('grad', '1_BASIC_INFO_FIX'), ('grad', '2_EMERGENCY_INFO_FIX'), ('grad', '3_EDUCATION_INFO_FIX'),
                             ('grad', '4_REFERENCES_INFO_FIX'), ('grad', '5_TEST_INFO_FIX'), ('grad', '6_LANGUAGES_INFO_FIX'),
                             ('grad', '7_AWARDS_INFO_FIX'), ('grad', '8_RESEARCH_INFO_FIX'), ('grad', '9_EMPLOYMENT_FILE_FIX'),
                             ('grad', 'PCS_Identifier'), ('ra', 'deletedContract')):
                    continue
                rows = self.row_count(d, t)
                print "%s.dbo.%s (%i)" % (d, t, rows)
                for name, typ, null, size in self.table_columns(d, t):
                    print "  %s %s(%s) (null %s)" % (name, typ, size, null.strip())
                print

class GradImport(object):
    IMPORT_USER = 'csilop'
    GENDER_MAP = {
                  'male': 'M',
                  'female': 'F',
                  'unknow': 'U',
                  }
    # names of the requirements, in the same order they appear in the query in process_grad
    REQ_LIST = ('Supervisory Committee', 'Breadth Program Approved', 'Breadth Requirements', 'Courses Completed',
                'Depth Exam', 'CMPT 891', 'Thesis Proposal', 'Thesis Defence', 'Research Topic')

    STATUS_MAP = {
                  'Incomplete': 'APPL',
                  'Partial': 'APPL',
                  'Expired': 'APPL',
                  'Complete': 'APPL', # TODO: confirm that "Complete" is really about the application
                  'Received': 'APPL', # TODO: confirm that "Received" is really about the application
                  'Hold(-)': 'APPL',
                  'Hold(+)': 'APPL',
                  'To Be Offered': 'APPL',
                  'OfferOut': 'APPL',
                  'Confirmed': 'APPL',
                  'Refused': 'APPL',
                  'Canceled': 'APPL',
                  'DeclinedOffer': 'APPL',
                  'Rejected': 'APPL',
                  'Active': 'ACTI',
                  'PartTime': 'PART',
                  'OnLeave': 'LEAV',
                  'Graduated': 'GRAD',
                  'Withdrawn': 'WIDR',
                  'ArchiveSP': 'ARSP',
                  }
    APP_STATUS_MAP = {
                      'Incomplete': 'INCO',
                      'Expired': 'INCO',
                      'Partial': 'INCO',
                      'Received': 'INCO',
                      'Complete': 'COMP',
                      'Hold(-)': 'HOLD',
                      'Hold(+)': 'HOLD',
                      'To Be Offered': 'HOLD',
                      'OfferOut': 'OFFO',
                      'Confirmed': 'CONF',
                      'DeclinedOffer': 'DECL',
                      'Refused': 'DECL', # TODO: is this different from DECL or REJE?
                      'Rejected': 'REJE',
                      'Canceled': 'REJE', # TODO: is this different from REJE?
                      } 
       
    def __init__(self):
        self.db = CortezConn()
        self.db.execute("USE [grad]", ())
        self.cs_setup()
    
    def cs_setup(self):
        print "Setting up CMPT grad programs..."
        cmpt = Unit.objects.get(slug='cmpt')
        programs = [('MSc Thesis', 'MSc Thesis option'), ('MSc Proj', 'MSc Project option'), ('PhD', 'PhD'),
                    ('Special', 'Special Arrangements'), ('Qualifying', 'Qualifying Student')]
        for lbl, dsc in programs:
            gp, new_gp = GradProgram.objects.get_or_create(unit=cmpt, label=lbl)
            if new_gp:
                gp.description = dsc
                gp.created_by = self.IMPORT_USER
                gp.modified_by = self.IMPORT_USER
                gp.save()

        self.PROGRAM_MAP = {
                   ('MSc', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'),
                   ('MSc', 'Project'): GradProgram.objects.get(unit__slug='cmpt', slug='mscproj'),
                   ('MSc', 'Course'): GradProgram.objects.get(unit__slug='cmpt', slug='mscproj'),
                   ('MSc', ''): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'), # ???
                   ('MSc', None): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'), # ???
                   ('PhD', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='phd'),
                   ('PhD', ''): GradProgram.objects.get(unit__slug='cmpt', slug='phd'),
                   ('PhD', None): GradProgram.objects.get(unit__slug='cmpt', slug='phd'),
                   ('Special', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='special'),
                   ('Special', ''): GradProgram.objects.get(unit__slug='cmpt', slug='special'),
                   ('Special', None): GradProgram.objects.get(unit__slug='cmpt', slug='special'),
                   ('Qualifying', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='qualifying'),
                   ('Qualifying', ''): GradProgram.objects.get(unit__slug='cmpt', slug='qualifying'),
                   }

    def get_semester_for_date(self, date):
        # guess relevant semester for given date
        s = Semester.objects.filter(start__lte=date+datetime.timedelta(days=7)).order_by('-start')[0]
        diff = date.date()-s.start
        if diff > datetime.timedelta(days=120):
            raise ValueError, "Couldn't find semester for %s." % (date)
        return s
            
    def find_supervisor(self, supname):
        """
        Find supervisor by userid if possible; return (Person, external).
        """
        people = Person.objects.filter(userid=supname)
        if people:
            person = people[0]
            external = None
        elif supname.islower() and len(supname) <= 8:
            # seems to be a userid that we can't find: store as best possible
            person = None
            external = supname + '@sfu.ca'
        else:
            person = None
            external = supname
        
        return person, external

    @transaction.commit_on_success
    def process_grad(self, cortezid, sin, emplid, email, birthdate, gender,
                     english, mothertoungue, canadian, passport, visa, status):
        """
        Process one imported student
        
        Argument list must be in the same order at the query in get_students below.
        """
        # TODO: should use get_person_grad for production run (but get_or_create is good enough for testing)
        p, new_person = Person.objects.get_or_create(emplid=emplid)
        #p = get_person_grad(emplid, commit=True)
        #new_person = False

        # get what we can from SIMS
        if new_person:
            lname, fname, mname, pfname, title = get_names(emplid)
            p.first_name = fname
            p.last_name = lname
            p.middle_name = mname
            p.pref_first_name = pfname
            p.config['title'] = title
        
        # fill in the Person object with Cortez data
        if email:
            if '@' in email: # seem to have some userids in there too: let those stay in Person.userid
                p.config['applic_email'] = email
        if birthdate:
            p.config['birthdate'] = birthdate.date().isoformat()
        p.config['gender'] = self.GENDER_MAP[gender.lower()]
        p.config['cortezid'] = cortezid
        
        p.save()
        #TODO: (mothertoungue, canadian, passport, visa, status)
        
        self.db.execute("SELECT Program, Degreetype, SemesterStarted, SemesterFinished, "
                        "SupComSelected, BreProApproved, BreReqCompleted, CourseReqCompleted, "
                        "DepExamCompleted, CMPT891Completed, ThProApproved, ThDefended, ReaTopicChosen, "
                        "Supervisor1, Supervisor2, Supervisor3, Supervisor4, CoSupervisor "
                        "FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        #sys.stdout.write('.')
        #sys.stdout.flush()

        for prog, progtype, sem_start, sem_finish, supcom, brepro, brereq, crscom, depexam, \
                cmpt891, thepro, thedef, reatop, sup1,sup2,sup3,sup4, cosup in self.db:
            try: sem_start = get_or_create_semester(sem_start)
            except ValueError: sem_start = None
            try: sem_finish = get_or_create_semester(sem_finish)
            except ValueError: sem_finish = None

            # get/create the GradStudent object
            if prog is None:
                # TODO: no program => don't import?
                continue

            prog = self.PROGRAM_MAP[(prog, progtype)]
            gs, new_gs = GradStudent.objects.get_or_create(person=p, program=prog)
            if new_gs:
                gs.created_by = self.IMPORT_USER
            gs.modified_by = self.IMPORT_USER
            gs.save()
            
            # fill in their completed requirements
            # order of reqs must match self.REQ_LIST
            reqs = (supcom, brepro, brereq, crscom, depexam, cmpt891, thepro, thedef, reatop)
            for completed, req_name in zip(reqs, self.REQ_LIST):
                if not completed or completed.lower() in ('not taken',):
                    continue
                
                req, _ = GradRequirement.objects.get_or_create(program=prog, description=req_name)
                try:
                    cr = CompletedRequirement.objects.get(requirement=req, student=gs)
                    new_cr = False
                except CompletedRequirement.DoesNotExist:
                    cr = CompletedRequirement(requirement=req, student=gs)
                    new_cr = True

                if new_cr: # if it was already there, don't bother fiddling with it
                    if completed.lower() == 'passed':
                        sem = sem_finish or sem_start
                        notes = 'No semester on cortez: used finishing semester.'
                    elif completed.lower() == 'waived':
                        sem = sem_finish or sem_start
                        notes = 'Waived'                        
                    else:
                        notes = None
                        try:
                            sem = get_or_create_semester(completed)
                        except ValueError:
                            sem = get_or_create_semester('0'+completed)
                    
                    #if not sem:
                    #    print sem, sem_finish, sem_start, `completed`
                    cr.semester = sem
                    cr.notes = notes
                    cr.save()
            
            # Supervisors
            for pos, supname in zip(range(1,5), [sup1,sup2,sup3,sup4]):
                if not supname: continue
                person, external = self.find_supervisor(supname)
                
                sups = Supervisor.objects.filter(student=gs, supervisor=person, external=external, position=pos)
                if sups:
                    sup = sups[0]
                else:
                    sup = Supervisor(student=gs, supervisor=person, external=external, position=pos)
                    sup.created_by = self.IMPORT_USER
                is_senior = pos==1 or (pos==2 and cosup)
                sup.supervisor_type = 'SEN' if is_senior else 'COM'
                sup.modified_by = self.IMPORT_USER
                try:
                    sup.save()
                except IntegrityError:
                    print "Duplicate supervisor position for %s: can't import" % (gs)
                    
            
            # TODO: potential supervisor, exam committee
            
            # Examining Committee
            self.db.execute("SELECT * "
                            "FROM ExamCommittee WHERE Identifier=%s", (cortezid,))
            self.db.execute("SELECT Chair, ExtName, ExtDep, ExtInst, ExtEmail, SFUExaminer "
                            "FROM ExamCommittee WHERE Identifier=%s", (cortezid,))
            for chair, extname, extdep, extinst, extemail, sfuexam in self.db:
                if chair:
                    person, external = self.find_supervisor(chair)
                    sups = Supervisor.objects.filter(student=gs, supervisor=person, external=external, supervisor_type='CHA')
                    if sups:
                        sup = sups[0]
                    else:
                        sup = Supervisor(student=gs, supervisor=person, external=external, supervisor_type='CHA')
                        sup.created_by = self.IMPORT_USER
                    sup.removed = False
                    sup.position = 0
                    sup.modified_by = self.IMPORT_USER
                    sup.save()
                
                if sfuexam:
                    person, external = self.find_supervisor(sfuexam)
                    sups = Supervisor.objects.filter(student=gs, supervisor=person, external=external, supervisor_type='SFU')
                    if sups:
                        sup = sups[0]
                    else:
                        sup = Supervisor(student=gs, supervisor=person, external=external, supervisor_type='SFU')
                        sup.created_by = self.IMPORT_USER
                    if extemail:
                        sup.set_email(extemail)
                    
                    sup.removed = False
                    sup.position = 0
                    sup.modified_by = self.IMPORT_USER
                    sup.save()
                
                if extname:
                    external = extname
                    if extdep:
                        external += ", " + extdep
                    if extinst:
                        external += ", " + extinst
                    sups = Supervisor.objects.filter(student=gs, supervisor=None, external=external, supervisor_type='EXT')
                    if sups:
                        sup = sups[0]
                    else:
                        sup = Supervisor(student=gs, supervisor=None, external=external, supervisor_type='EXT')
                        sup.created_by = self.IMPORT_USER
                    sup.removed = False
                    sup.position = 0
                    sup.modified_by = self.IMPORT_USER
                    sup.save()


            # Status and application status
            self.db.execute("SELECT Status, Date, AsOfSem "
                        "FROM Status WHERE Identifier=%s "
                        "ORDER BY Date", (cortezid,))
            app_st = 'UNKN'
            for status, date, semname in self.db:
                if semname:
                    sem = Semester.objects.get(name=semname)
                else:
                    sem = self.get_semester_for_date(date)
                
                if status == 'Arrived':
                    # TODO: okay to ignore? Sounds pointless.
                    continue

                # grab most-recent applicant status for the GradStudent
                if status in self.APP_STATUS_MAP:
                    app_st = self.APP_STATUS_MAP[status]

                # create/update GradStatus
                sts = GradStatus.objects.filter(student=gs, status=self.STATUS_MAP[status], start=sem)
                if sts:
                    st = sts[0]
                else:
                    st = GradStatus(student=gs, status=self.STATUS_MAP[status], start=sem, end=None)
                
                if date:
                    st.notes = 'Started %s' % (date.date())
                st.save(close_others=True)
                
            gs.application_status = app_st
            gs.save()

        
        
        



                

    
    def get_students(self):
        print "Importing grad students..."
        self.db.execute("SELECT pi.Identifier, pi.SIN, pi.StudentNumber, "
                        "pi.Email, pi.BirthDate, pi.Sex, pi.EnglishFluent, pi.MotherTongue, pi.Canadian, pi.Passport, "
                        "pi.Visa, pi.Status, pi.LastName FROM PersonalInfo pi "
                        "WHERE pi.StudentNumber not in (' ', 'na', 'N/A', 'NO', 'Not App.', 'N.A.', '-no-') "
                        #"AND pi.LastName in ('Baker', 'Bart', 'Cukierman', 'Fraser')" 
                        "AND pi.LastName LIKE 'Ji%%'" 
                        #"AND pi.LastName > 'U'" 
                        "ORDER BY pi.LastName"
                        , ())
        initial = None
        for row in list(self.db):
            emplid = row[2]
            i = row[-1][0].upper()
            if i != initial:
                print "  ", i
                initial = i
                time.sleep(1)
            if not(emplid.isdigit() and len(emplid)==9):
                # TODO: what about them and the other no-emplid rows?
                continue
            self.process_grad(*(row[:-1]))

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
                   'Office/Marking': 'OM',
                   'Office/Marking/Labs': 'OML',
                   'Development': 'OPL',
                   'CMPT': 'OPL',
                   'ARC': 'OPL',
                   'MTF': 'OPL',
                   'Course': 'OPL',
                   'course': 'OPL',
                   }
    CATEGORY_INDEX = {'GTA1': 0, 'GTA2': 1, 'UTA': 2, 'ETA': 3}
    
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
                           component='OPL', owner=self.UNIT, title=title)
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
        for off_id, semname, crsnumber, section, hasLabs, title in self.db:
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
            
            offerings = CourseOffering.objects.filter(subject=subject, number__startswith=number, semester__name=semname, section__startswith=section)
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
        
        self.offeringid_map = offeringid_map
        
        # drop in a file to cache over multiple runs
        fp = open("offering_map_cache.json", 'w')
        # convert offerings to offering.ids for JSON
        offeringid_map = dict([(k, offeringid_map[k].id) for k in offeringid_map])
        json.dump(offeringid_map, fp, indent=1)
        fp.close()
    
    @transaction.commit_on_success
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
            posting.config['payperiods'] = "%.1f" % ((end-start).total_seconds()/3600/24/14,) # close enough for the import
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
        posting.config['payperiods'] = "%.1f" % ((sem.end-sem.start).total_seconds()/3600/24/14,) # close enough for the import
        posting.save()
        return posting
    
    @transaction.commit_on_success
    def get_ta(self, off_id, bu, salary, schol, description, payst, payen, posnum, initial, cond, tssu, remarks, app_bu, emplid, cat, sin, status):
        """
        Process one TA
        
        Argument order must be the same as query in get_tas below.
        """
        if bu == 0:
            return
        if off_id not in self.offeringid_map:
            # TODO: Where did these offerings go? I'm troubled.
            print "missing offering_id:", off_id
            #self.db.execute("SELECT * FROM Offerings where Offering_id=%s", (off_id,))
            #print list(self.db)
            #self.db.execute("SELECT * FROM Offerings o, Resource_Semesters s "
            #            "WHERE o.Semester_ID=s.Semester_ID and o.Offering_id=%s", (off_id,))
            #print list(self.db)
            #self.db.execute("SELECT * FROM Offerings o,  Courses c "
            #            "WHERE  o.Course_ID=c.Course_ID and o.Offering_id=%s", (off_id,))
            #print list(self.db)
            return
        offering = self.offeringid_map[off_id]
        p = get_person(emplid, commit=True)

        if offering.semester.name == '1007':
            print offering, (off_id, bu, salary, schol, description, payst, payen, posnum, initial, cond, tssu, remarks, app_bu, emplid, cat, sin, status)
        else:
            return
        
        try:
            posting = TAPosting.objects.get(unit=self.UNIT, semester=offering.semester)
        except TAPosting.DoesNotExist:
            posting = self.create_fake_posting(offering.semester)
        
        # create TAApplication
        apps = TAApplication.objects.filter(posting=posting, person=p)
        if apps:
            app = apps[0]
        else:
            app = TAApplication(posting=posting, person=p)
        
        app.category = self.CATEGORY_MAP[cat]
        app.base_units = app_bu or 0
        app.sin = sin
        app.save()
        
        # create TAContract
        contracts = TAContract.objects.filter(posting=posting, application=app)
        if contracts:
            contract = contracts[0]
        else:
            contract = TAContract(posting=posting, application=app)

        try:
            pos_id = self.positions[posnum]
        except KeyError:
            pos_id = posting.config['accounts'][self.CATEGORY_INDEX[app.category]]
        
        contract.sin = sin
        contract.pay_start = payst or offering.semester.start
        contract.pay_end = payen or offering.semester.end
        contract.appt_category = app.category
        contract.position_number_id = pos_id
        contract.appt = self.INITIAL_MAP[initial]
        contract.pay_per_bu = "%.2f" % (salary/bu)
        contract.scholarship_per_bu = "%.2f" % (schol/bu)
        contract.deadline = posting.deadline()
        contract.appt_cond = bool(cond)
        contract.appt_tssu = bool(tssu)
        contract.status = 'SGN' if status=='accepted' else 'CAN'
        contract.remarks = remarks or ''
        contract.created_by = self.IMPORT_USER
        contract.save()
        
        # create TACourse
        crses = TACourse.objects.filter(course=offering, contract=contract)
        if crses:
            crs = crses[0]
        else:
            crs = TACourse(course=offering, contract=contract)
        
        crs.description = self.TA_DESC_MAP[description.split()[0]]
        crs.bu = bu
        crs.save()
        
        # TODO: do we care about course preferences or skills from application?

    
    def get_tas(self):  
        self.get_ta_postings()
        self.get_offering_map()
        print "Importing TAs..."
        
        #self.db.execute("SELECT * FROM tasearch.dbo.tainfo i "
        #                "WHERE i.familyName='Baker' or i.studNum='200022802'", ())
        #print list(self.db) 

        self.db.execute("SELECT o.Offering_ID, o.bu, o.salary, o.scholarship, o.description, "
                        "o.PayrollStartDate, o.PayrollEndDate, o.PositionNumber, o.initAppointment, "
                        "o.conditional, o.tssu, o.remarks, i.base, "
                        "i.studNum, i.category, i.socialInsurance, i.status FROM TAOffering o, tasearch.dbo.tainfo i "
                        "WHERE o.TA_ID=i.appId ORDER BY i.appYear", ()) # and i.appYear>'109' 
        for row in list(self.db):
            self.get_ta(*row)



#Introspection().print_schema()
tain = TAImport().get_tas()
#gradin = GradImport().get_students()

