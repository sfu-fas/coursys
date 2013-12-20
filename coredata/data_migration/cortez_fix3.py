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

    def get_semester_for_date(self, date):
        # guess relevant semester for given date
        s = Semester.objects.filter(start__lte=date+datetime.timedelta(days=10)).order_by('-start')[0]
        diff = date.date()-s.start
        if diff > datetime.timedelta(days=140):
            raise ValueError, "Couldn't find semester for %s." % (date)
        return s

    @transaction.atomic
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

            gss = GradStudent.objects.filter(person=p, program=prog, config__contains='"cortezid": "%s"' % (cortezid))
            if not gss:
                return
            assert gss.count()==1
            gs = gss[0]
            GradProgramHistory.objects.filter(student=gs).delete()

            # program changes
            self.db.execute("SELECT program, degreetype, date, asofsem "
                            "FROM Programs WHERE Identifier=%s", (cortezid,))
            count = 0
            for program, degreetype, date, semname in self.db:
                progr = self.PROGRAM_MAP[(program, degreetype)]
                sem = Semester.objects.get(name=semname)
                count += 1
                phs = GradProgramHistory.objects.filter(student=gs, program=progr, start_semester=sem)
                if phs:
                    ph = phs[0]
                else:
                    ph = GradProgramHistory(student=gs, program=progr, start_semester=sem)
                ph.starting = date
                ph.save()
        
            if not GradProgramHistory.objects.filter(student=gs):
                # no program history for this student
                stsem = gs.start_semester
                if not stsem:
                    st = GradStatus.objects.filter(student=gs).order_by('-start__name')[0]
                    stsem = st.start
                ph = GradProgramHistory(student=gs, program=gs.program, start_semester=stsem)
                ph.save()
    
    def get_students(self):
        print "Importing grad students..."
        
        me = GradStudent.objects.get(slug='ggbaker-mscthesis')
        assert 'cortezid' in me.config
        
        self.db.execute("SELECT pi.Identifier, pi.SIN, pi.StudentNumber, "
                        "pi.Email, pi.BirthDate, pi.Sex, pi.EnglishFluent, pi.MotherTongue, pi.Canadian, pi.Passport, "
                        "pi.Visa, pi.Status, pi.LastModified, pi.LastName FROM PersonalInfo pi "
                        "WHERE pi.StudentNumber not in (' ', 'na', 'N/A', 'NO', 'Not App.', 'N.A.', '-no-') " 
                        #"AND LastName in ('Aghaee','Artner') " 
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


if __name__ == '__main__':
    gi=GradImport()
    gi.get_students()


