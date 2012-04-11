import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.db import transaction
from coredata.queries import DBConn, get_names
from coredata.models import Person
from grad.models import GradProgram, GradStudent

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
            if d in ('tasearch', 'master', 'msdb', 'pubs', 'faculty'):
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
                print "%s.%s (%i)" % (d, t, rows)
                for name, typ, null, size in self.table_columns(d, t):
                    print "  %s %s(%s) (null %s)" % (name, typ, size, null.strip())
                print

class GradImport(object):
    def __init__(self):
        self.db = CortezConn()
        self.db.execute("USE [grad]", ())
        
    GENDER_MAP = {
                  'male': 'M',
                  'female': 'F',
                  'unknow': 'U',
                  }
    PROGRAM_MAP = {
                   ('MSc', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'),
                   ('MSc', 'Project'): GradProgram.objects.get(unit__slug='cmpt', slug='mscproj'),
                   ('MSc', 'Course'): GradProgram.objects.get(unit__slug='cmpt', slug='mscproj'),
                   ('MSc', ''): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'), # ???
                   ('MSc', None): GradProgram.objects.get(unit__slug='cmpt', slug='mscthesis'), # ???
                   ('PhD', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='phd'),
                   ('PhD', ''): GradProgram.objects.get(unit__slug='cmpt', slug='phd'),
                   ('Special', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='special'),
                   ('Special', ''): GradProgram.objects.get(unit__slug='cmpt', slug='special'),
                   ('Qualifying', 'Thesis'): GradProgram.objects.get(unit__slug='cmpt', slug='qualifying'),
                   ('Qualifying', ''): GradProgram.objects.get(unit__slug='cmpt', slug='qualifying'),
                   }
    
    @transaction.commit_on_success
    def process_grad(self, cortezid, sin, emplid, email, birthdate, gender,
                     english, mothertoungue, canadian, passport, visa, status):
        """
        Process one 
        
        Argument list must be in the same order at the query in get_students below.
        """
        if not(emplid.isdigit() and len(emplid)==9):
            # TODO what about them?
            return

        p, new_person = Person.objects.get_or_create(emplid=emplid)

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
        
        #print
        #print p.__dict__
        p.save()
        #print (mothertoungue, canadian, passport, visa, status)
        
        self.db.execute("SELECT * FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        self.db.execute("SELECT Program, Degreetype, SemesterStarted, SemesterFinished FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        for prog, progtype, sem_start, sem_finish in self.db:
            # get/create the GradStudent object
            prog = self.PROGRAM_MAP[(prog, progtype)]
            gs = GradStudent.objects.get_or_create(person=p, program=prog)
            #gs.save()

            

    
    def get_students(self):
        #self.db.execute("select Identifier, Category, StudentNumber, SIN from PersonalInfo", ())
        self.db.execute("SELECT pi.Identifier, pi.SIN, pi.StudentNumber, "
                        "pi.Email, pi.BirthDate, pi.Sex, pi.EnglishFluent, pi.MotherTongue, pi.Canadian, pi.Passport, "
                        "pi.Visa, pi.Status FROM PersonalInfo pi "
                        "WHERE pi.StudentNumber not in (' ', 'na', 'N/A', 'NO', 'Not App.', 'N.A.', '-no-') " 
                        , ())
        for row in list(self.db):
            self.process_grad(*row)
            
            
            

#Introspection().print_schema()
gradin = GradImport()
gradin.get_students()

