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
    CAMPUS_MAP = {
                  '': None,
                  'both': 'MULTI',
                  'Sry': 'SURRY',
                  'Bby': 'BRNBY',
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

            gss = GradStudent.objects.filter(person=p, program=prog, config__contains='"cortezid": "%s"' % (cortezid))
            if not gss:
                return
            assert gss.count()==1
            gs = gss[0]
            
            self.db.execute("SELECT SIN "
                        "FROM PersonalInfo WHERE Identifier=%s", (cortezid,))
            for sin, in list(self.db):
                if sin and len(sin)==9 and sin.isdigit():
                    gs.set_sin(sin)
                    gs.save()
            
            
    
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


