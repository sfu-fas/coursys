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

import pymssql, MySQLdb
CORTEZ_USER = 'ggbaker'

# with the Ubuntu package python-pymssql, this change must be made
# in /etc/freetds/freetds.conf: [http://www.freetds.org/userguide/choosingtdsprotocol.htm]
# [global]
#    tds version = 7.0
# or run with
#   TDSVER=7.0 python coredata/cortez_fix.py

# https://bugs.launchpad.net/ubuntu/+source/pymssql/+bug/918896

# needs these ports forwarded to the databases:
#   ssh -L 1433:cortez.cs.sfu.ca:1433 oak.fas.sfu.ca # cortez DB
#   ssh -L 4000:localhost:4000 -L 50000:localhost:50000 courses.cs.sfu.ca # AMAINT and SIMS

# ln -s /usr/lib/pyshared/python2.7/pymssql.so ../lib/python2.7/site-packages/
# ln -s /usr/lib/pyshared/python2.7/_mssql.so ../lib/python2.7/site-packages/


# update weird value from test data
Unit.objects.filter(slug='comp').update(label='CMPT', slug='cmpt')


NEW_STATUSES = [
   {
   "end": None, 
   "hidden": False, 
   "notes": "", 
   "start_id": 20, 
   "start_date": None, 
   "status": "CONF", 
   "student_id": 3682, 
   },
   {
   "end": None, 
   "hidden": False, 
   "notes": "", 
   "start_id": 20, 
   "start_date": None, 
   "status": "CONF", 
   "student_id": 3537, 
   },
   {
   "end": None, 
   "hidden": False, 
   "notes": "", 
   "start_id": 20, 
   "start_date": None, 
   "status": "CONF", 
   "student_id": 1772
   },
   {
   "end": None, 
   "hidden": False, 
   "notes": "", 
   "start_id": 20, 
   "start_date": None, 
   "status": "CONF", 
   "student_id": 851
   }
]


class CortezConn(DBConn):
    db_host = '127.0.0.1'
    db_user = "fas.sfu.ca\\" + CORTEZ_USER
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
    REQ_OBSOLETE = ('CMPT 891',) # can be hidden
    BOOL_LOOKUP = {'yes': True, 'no': False}

    # cortez -> coursys status values
    STATUS_MAP = {
                  'Incomplete': 'INCO',
                  'Partial': 'INCO',
                  'Expired': 'EXPI',
                  'Complete': 'COMP',
                  'Received': 'COMP',
                  'Hold(-)': 'HOLD',
                  'Hold(+)': 'HOLD',
                  'To Be Offered': 'OFFO',
                  'OfferOut': 'OFFO',
                  'Confirmed': 'CONF',
                  'Refused': 'REJE', # note: not realy used, so collapsed into other category
                  'Canceled': 'CANC',
                  'DeclinedOffer': 'DECL',
                  'expired': 'DECL',
                  'Rejected': 'REJE',
                  'Arrived': 'ARIV',
                  'Active': 'ACTI',
                  'PartTime': 'PART',
                  'OnLeave': 'LEAV',
                  'Graduated': 'GRAD',
                  'Withdrawn': 'WIDR',
                  'ArchiveSP': 'ARSP',
                  }

    LETTER_TEMPLATES = [
            ("MSc Invite", "Dear {{ title }} {{ last_name }},\r\n\r\nOn behalf of the School of Computing Science I am pleased to inform you that you have been admitted to the {{ program }} starting in {{ start_semester }}.\r\n\r\nWe are able to provide you with financial support in the amount of $XXXX per year for YYY year(s) in the program, given you make satisfactory progress, from a variety of sources including: research and teaching assistant appointments, graduate fellowships, scholarships, etc. Should you receive an external award (i.e. NSERC) to support your studies, financial support from SFU will instead consist of a minimum $6,000 \"top up\" per annum while you hold the external award, again from a variety of sources. You can expect continued funding for subsequent years, again subject to satisfactory progress and performance in course work and research towards the completion of your degree, and the continued availability of funding.\r\n\r\nSFU has 3 semesters per year. The typical time to complete the MSc program is 6 to 8 semesters and 12 to 15 semesters for the PhD program.\r\n\r\nIf you are an International Student you are required to obtain a study permit from Immigration Canada before you can begin your program. You will need to provide Immigration officials with an official letter of admission and a letter of acceptance which are both issued by the Dean of Graduate Studies offices. Please contact the nearest Canadian Embassy or High Commission for information on obtaining a study permit.\r\n\r\nPlease note that the financial support that we offer does not include tuition fees. The current tuition fees for Simon Fraser University graduate students are $1,661.60 per semester (or $4,984.80 per year), although it is possible there may be an increase in the Fall {{ start_year }}.\r\n\r\nDr. {{ supervisor_name }} has been assigned to be your potential supervisor and we ask that you please contact  {{ supervisor_himher }}  prior to your arrival at SFU. Dr. {{ supervisor_name }} may remain your permanent supervisor, but if this is not the case, {{ supervisor_heshe }} and I will work with you to choose a different supervisor who is more suited to your interests and needs.\r\n\r\nPlease reply as soon as possible whether you intend to register in the Spring 2013 semester and accept the financial support offered. This offer is valid until October 18th, 2012. If you have any questions or require clarification, please feel free to contact Dr. {{ supervisor_name }} ({{ supervisor_email }}) or our Graduate Program Assistant, Val Galat (csgrada@sfu.ca).\r\n\r\nWe are looking forward to your arrival and if you require assistance, please do not hesitate to contact us.", False),
            ("PhD Invite", "Dear {{ title }} {{ last_name }},\r\n\r\nOn behalf of the School of Computing Science I am pleased to inform you that you have been admitted to the {{ program }} starting in {{ start_semester }}.\r\n\r\nWe are able to provide you with financial support in the amount of {{ promise }} per year for YYY year(s) in the program, given you make satisfactory progress, from a variety of sources including: research and teaching assistant appointments, graduate fellowships, scholarships, etc. Should you receive an external award (i.e. NSERC) to support your studies, financial support from SFU will instead consist of a minimum $6,000 \"top up\" per annum while you hold the external award, again from a variety of sources. You can expect continued funding for subsequent years, again subject to satisfactory progress and performance in course work and research towards the completion of your degree, and the continued availability of funding.\r\n\r\nSFU has 3 semesters per year. The typical time to complete the MSc program is 6 to 8 semesters and 12 to 15 semesters for the PhD program.\r\n\r\nIf you are an International Student you are required to obtain a study permit from Immigration Canada before you can begin your program. You will need to provide Immigration officials with an official letter of admission and a letter of acceptance which are both issued by the Dean of Graduate Studies offices. Please contact the nearest Canadian Embassy or High Commission for information on obtaining a study permit.\r\n\r\nPlease note that the financial support that we offer does not include tuition fees. The current tuition fees for Simon Fraser University graduate students are $1,661.60 per semester (or $4,984.80 per year), although it is possible there may be an increase in the Fall {{ start_year }}.\r\n\r\nDr. {{ supervisor_name }} has been assigned to be your potential supervisor and we ask that you please contact {{ supervisor_himher }} prior to your arrival at SFU. Dr. {{ supervisor_name }} may remain your permanent supervisor, but if this is not the case, {{ supervisor_heshe }} and I will work with you to choose a different supervisor who is more suited to your interests and needs.\r\n\r\nPlease reply as soon as possible whether you intend to register in the Spring 2013 semester and accept the financial support offered. This offer is valid until October 18th, 2012. If you have any questions or require clarification, please feel free to contact Dr. {{ supervisor_name }} ({{ supervisor_email }}) or our Graduate Program Assistant, Val Galat (csgrada@sfu.ca).\r\n\r\nWe are looking forward to your arrival and if you require assistance, please do not hesitate to contact us.", False),
            ("Special Student invite", "Dear {{ title }} {{ last_name }},\r\n\r\nOn behalf of the School of Computing Science, I am pleased to inform you that we have recommended to the University's Senate Graduate Studies Committee that you be admitted as a SPECIAL student in the {{ start_semester }} semester, to complete the following course:\r\n\r\nCMPT XXX\r\n\r\nAs a Special Student you are not taking courses toward a degree, diploma or certificate at this institution but merely taking courses for your professional development. This admission is for the {{ start_semester }} semester only. You must reapply for each semester you want to study. Please do so in a timely manner.\r\n\r\nYour application has been forwarded to the Senate Graduate Studies Committee for final approval. Upon approval of admission from them kindly confirm as soon as possible if you intend to be registered for the {{ start_semester }} semester. On arrival, make arrangements with the Graduate Program assistant to register you in your classes.\r\n", False),
            ("Visa letter", "This is to confirm that {{ title }} {{ first_name }} {{ last_name }} is currently a full-time graduate student in the School of Computing Science at Simon Fraser University in a program of studies leading to the {{ program }} degree.\r\n\r\n{{ title }} {{ last_name }} is currently employed in the School of Computing Science, as a {{ recent_empl }}. This employment is an integral part of {{ his_her }} course studies towards the {{ program }} degree. Simon Fraser University operates on a trimester system, so that students are supported for three semesters each year, providing a yearly support level of {{ promise }}. The tuition fee at Simon Fraser University at graduate school is $4,984.80 per year.\r\n\r\n{{ title }} {{ last_name }} is making satisfactory progress towards the completion of {{ his_her }} degree and can expect to receive income at this rate in the future until the degree program has been completed. {{ title }} {{ last_name }} is expected to complete {{ his_her }} studies by MONTH_AND_YEAR.", False),
            ("International letter", "This is to advise you that {{ title }} {{ first_name }} {{ last_name }}, a {{ program }} Student in the School of Computing Science, has been employed as follows.\r\n\r\n{% if tafunding %}Teaching assistant responsibilities include providing tutorials, office hours and marking assignments. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ tafunding }}{% endif %}\r\n{% if rafunding %}Research assistants assist/provide research services to faculty. {{title}} {{last_name}}'s assignments have been:\r\n\r\n{{ rafunding }}{% endif %}\r\n{% if scholarships %}{{title}} {{last_name}} has received the following scholarships:\r\n\r\n{{ scholarships }}{% endif %}\r\n\r\n{{ title }} {{ last_name }} is making satisfactory progress toward the completion of {{ his_her }} degree and is expected to complete {{ his_her }} studies by MONTH YEAR.\r\n", False),
            ("Cortez Import", '', True),
            ]
    GRAD_FLAGS = ['GDDP', 'Co-op']
    LETTER_TYPE_MAP = {
            'OFR_PHD': "PhD Invite",
            'OFR_MSC': "MSc Invite",
            'OFR_QUALIFYING': 'Special Student invite',
            'OFR_SPECIAL': 'Special Student invite',
            }
    COMMENT_TYPE_MAP = {
            'Schol': 'SCO',
            'Other': 'OTH',
            'None': 'OTH',
            'RA': 'RA',
            'TA': 'TA',
            }

    def __init__(self):
        self.db = CortezConn()
        self.db.execute("USE [grad]", ())
        self.cs_setup()
        self.get_ra_map()
        self.make_future_semesters()
    
    def get_ra_map(self):
        self.ra_map = {}
        for appt in RAAppointment.objects.filter(unit=self.unit):
            if 'cortezid' in appt.config:
                self.ra_map[appt.config['cortezid']] = appt
    
    def make_semester(self, name, start, end):
        s = Semester(name=name, start=start, end=end)
        s.save()
        
        first_monday = start
        while first_monday.weekday() != 0:
            first_monday += datetime.timedelta(days=1)    
        wk = SemesterWeek(semester=s, week=1, monday=first_monday)
        wk.save()

    def make_future_semesters(self):
        """
        There are some scholarships far in the future: must create those Semester objects manually.
        """
        try: Semester.objects.get(name='1141')
        except Semester.DoesNotExist: self.make_semester('1141', datetime.date(2014,1,1), datetime.date(2014,4,30))
        try: Semester.objects.get(name='1144')
        except Semester.DoesNotExist: self.make_semester('1144', datetime.date(2014,5,1), datetime.date(2014,8,30))
        try: Semester.objects.get(name='1147')
        except Semester.DoesNotExist: self.make_semester('1147', datetime.date(2014,9,1), datetime.date(2014,12,30))
        try: Semester.objects.get(name='1151')
        except Semester.DoesNotExist: self.make_semester('1151', datetime.date(2015,1,1), datetime.date(2015,4,30))
        try: Semester.objects.get(name='1154')
        except Semester.DoesNotExist: self.make_semester('1154', datetime.date(2015,5,1), datetime.date(2015,8,30))
        try: Semester.objects.get(name='1157')
        except Semester.DoesNotExist: self.make_semester('1157', datetime.date(2015,9,1), datetime.date(2015,12,30))
        try: Semester.objects.get(name='1161')
        except Semester.DoesNotExist: self.make_semester('1161', datetime.date(2016,1,1), datetime.date(2016,4,30))
        try: Semester.objects.get(name='1164')
        except Semester.DoesNotExist: self.make_semester('1164', datetime.date(2016,5,1), datetime.date(2016,8,30))
        try: Semester.objects.get(name='1167')
        except Semester.DoesNotExist: self.make_semester('1167', datetime.date(2016,9,1), datetime.date(2016,12,30))
        try: Semester.objects.get(name='1171')
        except Semester.DoesNotExist: self.make_semester('1171', datetime.date(2017,1,1), datetime.date(2017,4,30))
        try: Semester.objects.get(name='1174')
        except Semester.DoesNotExist: self.make_semester('1174', datetime.date(2017,5,1), datetime.date(2017,8,30))
        try: Semester.objects.get(name='1177')
        except Semester.DoesNotExist: self.make_semester('1177', datetime.date(2017,9,1), datetime.date(2017,12,30))
        
        
        
    def cs_setup(self):
        print "Setting up CMPT grad programs..."
        cmpt = Unit.objects.get(slug='cmpt')
        self.unit = cmpt
        programs = [('MSc Thesis', 'MSc Thesis option'), ('MSc Proj', 'MSc Project option'),
                    ('MSc Course', 'MSc Course option'), ('PhD', 'PhD'),
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
                   ('MSc', 'Course'): GradProgram.objects.get(unit__slug='cmpt', slug='msccourse'),
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
        
        for label, content, hidden in self.LETTER_TEMPLATES:
            try:
                template = LetterTemplate.objects.get(unit=cmpt, label=label)
            except LetterTemplate.DoesNotExist:
                template = LetterTemplate(unit=cmpt, label=label, content=content, created_by='csilop', hidden=hidden)
                template.save()
            
            if hidden:
                # the hidden one is the default for imports
                self.template = template  
        
        for label in self.GRAD_FLAGS:
            try:
                GradFlag.objects.get(unit=cmpt, label=label)
            except GradFlag.DoesNotExist:
                GradFlag(unit=cmpt, label=label).save()
        

    def get_semester_for_date(self, date):
        # guess relevant semester for given date
        s = Semester.objects.filter(start__lte=date+datetime.timedelta(days=10)).order_by('-start')[0]
        diff = date.date()-s.start
        if diff > datetime.timedelta(days=140):
            raise ValueError, "Couldn't find semester for %s." % (date)
        return s
            
    def find_supervisor(self, supname):
        """
        Find supervisor by userid if possible; return (Person, external).
        """
        if supname == 'mitchell':
            supname = 'dgm'
        person = get_person_by_userid(supname)
        if person:
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
                     english, mothertoungue, canadian, passport, visa, currentstatus, lastmod):
        """
        Process one imported student
        
        Argument list must be in the same order at the query in get_students below.
        """
        try:
            p = Person.objects.get(emplid=emplid)
        except (ValueError, Person.DoesNotExist):
            return
        
        self.db.execute("SELECT Program, Degreetype, SemesterStarted, SemesterFinished, "
                        "SupComSelected, BreProApproved, BreReqCompleted, CourseReqCompleted, "
                        "DepExamCompleted, CMPT891Completed, ThProApproved, ThDefended, ReaTopicChosen, "
                        "Supervisor1, Supervisor2, Supervisor3, Supervisor4, CoSupervisor, Sponsor, ResearchArea "
                        "FROM AcademicRecord WHERE Identifier=%s", (cortezid,))
        
        for prog, progtype, sem_start, sem_finish, supcom, brepro, brereq, crscom, depexam, \
                cmpt891, thepro, thedef, reatop, sup1,sup2,sup3,sup4, cosup, sponsor, research in list(self.db):
            try: sem_start = get_or_create_semester(sem_start)
            except ValueError: sem_start = None
            try: sem_finish = get_or_create_semester(sem_finish)
            except ValueError: sem_finish = None

            # get/create the GradStudent object
            if prog is None:
                # no program => don't import
                # all seem to start in 2006/2007 and have no end date
                continue

            prog = self.PROGRAM_MAP[(prog, progtype)]

            gs = GradStudent.objects.get(person=p, program=prog, config__contains='"cortezid": "%s"' % (cortezid))
            #print gs
            GradStatus.objects.filter(student=gs).delete()
            
            # Status and application status
            self.db.execute("SELECT Status, Date, AsOfSem "
                        "FROM Status WHERE Identifier=%s "
                        "ORDER BY Date", (cortezid,))
            for status, date, semname in list(self.db):
                if semname:
                    sem = Semester.objects.get(name=semname)
                else:
                    sem = self.get_semester_for_date(date)

                # create/update GradStatus
                sts = GradStatus.objects.filter(student=gs, status=self.STATUS_MAP[status], start=sem)
                if sts:
                    st = sts[0]
                else:
                    st = GradStatus(student=gs, status=self.STATUS_MAP[status], start=sem, end=None)
                
                if date:
                    st.start_date = date.date()
                st.save(close_others=True)


            # check that the cortez current status is the one we're displaying/using
            curr_st = self.STATUS_MAP[currentstatus]
            sts = GradStatus.objects.filter(student=gs, status=curr_st).order_by('-start__name')
            if sts:
                st = sts[0]
            else:
                st = GradStatus(student=gs, status=curr_st, start=Semester.get_semester(lastmod))
            st.end = None
            st.save()
            gs.update_status_fields()
            assert curr_st == gs.current_status

    
    def get_students(self):
        print "Importing grad students..."
        
        me = GradStudent.objects.get(slug='ggbaker-mscthesis')
        assert 'cortezid' in me.config
        
        self.db.execute("SELECT pi.Identifier, pi.SIN, pi.StudentNumber, "
                        "pi.Email, pi.BirthDate, pi.Sex, pi.EnglishFluent, pi.MotherTongue, pi.Canadian, pi.Passport, "
                        "pi.Visa, pi.Status, pi.LastModified, pi.LastName FROM PersonalInfo pi "
                        "WHERE pi.StudentNumber not in (' ', 'na', 'N/A', 'NO', 'Not App.', 'N.A.', '-no-') " 
                        #"AND LastName in ('Nosrati','Artner') " 
                        "ORDER BY pi.LastName"
                        , ())
        
        initial = None
        for row in list(self.db):
            i = row[-1][0].upper()
            if i != initial:
                print "  ", i
                initial = i
                time.sleep(0.5)
            try:
                self.process_grad(*(row[:-1]))
            except:
                print row
                raise

    @transaction.commit_on_success
    def restore_new(self):
        for data in NEW_STATUSES:
            st = GradStatus(**data)
            print st

if __name__ == '__main__':
    gi=GradImport()
    gi.get_students()
    gi.restore_new()

