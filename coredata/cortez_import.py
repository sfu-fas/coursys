import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.db import transaction
from coredata.queries import DBConn, get_names, get_or_create_semester
from coredata.models import Person, Semester, Unit, CourseOffering
from grad.models import GradProgram, GradStudent, GradRequirement, CompletedRequirement
from ta.models import TAContract, TAApplication, TAPosting, TACourse
from ta.models import Account
from coredata.importer_rodb import get_person, get_person_grad
import datetime

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
    # names of the requirements, in the same order they appear in the import logic
    REQ_LIST = ('Supervisory Committee', 'Breadth Program Approved', 'Breadth Requirements', 'Courses Completed',
                'Depth Exam', 'CMPT 891', 'Thesis Proposal', 'Thesis Defence', 'Research Topic')
    
    def __init__(self):
        self.db = CortezConn()
        self.db.execute("USE [grad]", ())
    
    def cs_setup(self):
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


            
    @transaction.commit_on_success
    def process_grad(self, cortezid, sin, emplid, email, birthdate, gender,
                     english, mothertoungue, canadian, passport, visa, status):
        """
        Process one imported student
        
        Argument list must be in the same order at the query in get_students below.
        """
        if not(emplid.isdigit() and len(emplid)==9):
            # TODO: what about them?
            return

        #p, new_person = Person.objects.get_or_create(emplid=emplid)
        p = get_person_grad(emplid, commit=True)
        new_person = False

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
        #print (mothertoungue, canadian, passport, visa, status)
        
        #self.db.execute("SELECT * FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        self.db.execute("SELECT Program, Degreetype, SemesterStarted, SemesterFinished, "
                        "SupComSelected, BreProApproved, BreReqCompleted, CourseReqCompleted, "
                        "DepExamCompleted, CMPT891Completed, ThProApproved, ThDefended, ReaTopicChosen "
                        "FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        sys.stdout.write('.')
        sys.stdout.flush()

        for prog, progtype, sem_start, sem_finish, supcom, brepro, brereq, crscom, depexam, cmpt891, thepro, thedef, reatop  in self.db:
            try: sem_start = get_or_create_semester(sem_start)
            except ValueError: sem_start = None
            try: sem_finish = get_or_create_semester(sem_finish)
            except ValueError: sem_finish = None

            # get/create the GradStudent object
            if prog is None:
                # TODO: ???
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
                cr, new_cr = CompletedRequirement.objects.get_or_create(requirement=req, student=gs)
                if new_cr: # if it was already there, don't bother fiddling with it
                    if completed.lower() == 'passed':
                        sem = sem_finish
                        print `sem`
                        notes = 'No semester on cortez: used finishing semester.'
                    else:
                        notes = None
                        try:
                            sem = get_or_create_semester(completed)
                        except ValueError:
                            sem = get_or_create_semester('0'+completed)

                    cr.semester = sem
                    cr.notes = notes
                    cr.save()
            
            # statuses


                
            
            
                

            

    
    def get_students(self):
        #self.db.execute("select Identifier, Category, StudentNumber, SIN from PersonalInfo", ())
        self.db.execute("SELECT pi.Identifier, pi.SIN, pi.StudentNumber, "
                        "pi.Email, pi.BirthDate, pi.Sex, pi.EnglishFluent, pi.MotherTongue, pi.Canadian, pi.Passport, "
                        "pi.Visa, pi.Status FROM PersonalInfo pi "
                        "WHERE pi.StudentNumber not in (' ', 'na', 'N/A', 'NO', 'Not App.', 'N.A.', '-no-') "
                        #"AND pi.LastName LIKE 'Ba%%'" 
                        , ())
        for row in list(self.db):
            self.process_grad(*row)
            


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
                    }
    INITIAL_MAP = {
                   'yes': 'INIT',
                   'no': 'REAP',
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
        
    
    def get_offering_map(self):
        offeringid_map = {}
        self.db.execute("SELECT Offering_ID, Semester_Description, Course_Number, Section, o.hasLabs from Offerings o, Resource_Semesters s, Courses c "
                        "WHERE o.Semester_ID=s.Semester_ID AND o.Course_ID=c.Course_ID", ())
        for off_id, semname, crsnumber, section, hasLabs in self.db:
            subject, number = crsnumber.split()
            offerings = CourseOffering.objects.filter(subject=subject, number__startswith=number, semester__name=semname, section__startswith=section)
            #print (off_id, semname, crsnumber, section, hasLabs)
            if offerings.count() > 1:
                raise ValueError, "multiple offerings found: " + str(offerings)
            elif offerings:
                o = offerings[0]
                offeringid_map[off_id] = o
                o.set_labtas(bool(hasLabs))
                o.save()
        
        return offeringid_map
    
    def get_ta_postings(self):
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
            salary = [gta1a,gta2a,etaa,utaa]
            schol = [gta1s,gta2s,etas,utas]
            positions = [gta1p,gta2p,etap,utap]
            positions = [self.positions[p] for p in positions]
            
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
    
    
    def get_tas(self):            
        self.get_ta_postings()
        offeringid_map = self.get_offering_map()

        self.db.execute("SELECT o.Offering_ID, o.bu, o.salary, o.scholarship, o.description, "
                        "o.PayrollStartDate, o.PayrollEndDate, o.PositionNumber, o.initAppointment, "
                        "o.conditional, o.tssu, o.remarks, i.base, "
                        "i.studNum, i.category, i.socialInsurance, i.status FROM TAOffering o, tasearch.dbo.tainfo i "
                        "WHERE o.TA_ID=i.appId", ())
        for off_id, bu, salary, schol, description, payst, payen, posnum, initial, cond, tssu, remarks, app_bu, emplid, cat, sin, status in self.db:
            #print (off_id, bu, salary, schol, pos_num, emplid, cat, sin, status)
            if bu == 0:
                continue
            if off_id not in offeringid_map:
                continue
            offering = offeringid_map[off_id]
            p = get_person(emplid, commit=True)
            posting = TAPosting.objects.get(unit=self.UNIT, semester=offering.semester)
            
            # create TAApplication
            apps = TAApplication.objects.filter(posting=posting, person=p)
            if apps:
                app = apps[0]
            else:
                app = TAApplication(posting=posting, person=p)
            
            app.category = self.CATEGORY_MAP[cat]
            app.base_units = app_bu
            app.sin = sin
            app.save()
            
            # create TAContract
            contracts = TAContract.objects.filter(posting=posting, application=app)
            if contracts:
                contract = contracts[0]
            else:
                contract = TAContract(posting=posting, application=app)
            
            contract.sin = sin
            contract.pay_start = payst
            contract.pay_end = payen
            contract.appt_category = app.category
            contract.position_number_id = self.positions[posnum]
            contract.appt = self.INITIAL_MAP[initial]
            contract.pay_per_bu = "%.2f" % (salary/bu)
            contract.scholarship_per_bu = "%.2f" % (schol/bu)
            contract.deadline = posting.deadline()
            contract.appt_cond = cond
            contract.appt_tssu = tssu
            contract.status = 'SGN' if status=='accepted' else 'REJ'
            contract.remarks = remarks or ''
            contract.created_by = self.IMPORT_USER
            contract.save()
            
            # create TACourse
            crses = TACourse.objects.filter(course=offering, contract=contract)
            if crses:
                crs = crses[0]
            else:
                crs = TACourse(course=offering, contract=contract)
            
            crs.description = description
            crs.bu = bu
            crs.save()



#Introspection().print_schema()
#gradin = GradImport()
#gradin.cs_setup()
#gradin.get_students()
tain = TAImport()
tain.get_tas()

