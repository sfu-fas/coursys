from django.core.management.base import BaseCommand
from coredata.models import Semester, Unit
from courselib.testing import create_fake_semester, TEST_COURSE_SLUG
from grad.models import GradProgram, GradStudent, GradProgramHistory, ScholarshipType, Scholarship, OtherFunding, Promise

def get_or_create_nosave(Model, **kwargs):
    try:
        m = Model.objects.get(**kwargs)
    except Model.DoesNotExist:
        m = Model(**kwargs)
    return m


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def handle(self, *args, **options):
        self.student_data()

    def student_data(self):
        """
        Give one lucky student some more data that we can work wtih.
        """
        cmpt = Unit.objects.get(slug='cmpt')
        msc = GradProgram.objects.get(unit=cmpt, slug='mscthesis')
        phd = GradProgram.objects.get(unit=cmpt, slug='phd')
        gs = GradStudent.objects.get(person__userid='0xxxgrad', program__unit=cmpt)
        start = Semester.current().offset(-3)

        # create some program history
        ph = get_or_create_nosave(GradProgramHistory, student=gs, program=msc)
        ph.start_semester = start
        ph.save()
        ph = get_or_create_nosave(GradProgramHistory, student=gs, program=phd)
        ph.start_semester = start.offset(3)
        ph.save()
        
        # give him some money
        stype = ScholarshipType.objects.filter(unit=cmpt)[0]
        sch = get_or_create_nosave(Scholarship, student=gs, scholarship_type=stype)
        sch.amount = 2000
        sch.start_semester = start
        sch.end_semester = start.offset(2)
        sch.save()
        
        of = get_or_create_nosave(OtherFunding, student=gs, semester=start.offset(3))
        of.amount = 1300
        of.description = "Money fell from the sky"
        of.save()
        
        # promise
        p = get_or_create_nosave(Promise, student=gs, start_semester=start)
        p.end_semester = start.offset(2)
        p.amount = 10000
        p.save()
        p = get_or_create_nosave(Promise, student=gs, start_semester=start.offset(3))
        p.end_semester = start.offset(5)
        p.amount = 10000
        p.save()
        

