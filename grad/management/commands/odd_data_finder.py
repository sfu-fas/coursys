"""
Find strange data in the Grad database

"""

from django.core.management.base import BaseCommand, CommandError
from coredata.models import Person, Unit, Role, Semester
from grad.models import GradStudent, GradProgram, GradStatus, GradProgramHistory


class Command(BaseCommand):
    """ Usage: 
        python manage.py odd_data_finder
    """
    args = 'none'
    help = 'Print out students who have oddly-shaped data'
        
    option_list = BaseCommand.option_list + (
        )
    
    def handle(self, *args, **options):
        #graduated_students_who_are_not_graduated()
        #declined_offer_before_active_status()
        withdrawn_before_active_status()

def cmpt_grad_students():
    unit = Unit.objects.get(label="CMPT")
    grad_students = GradStudent.objects.filter(program__unit=unit)
    return grad_students

def print_student(student, list_of_status_semester_pairs):
    print(student)
    print("https://courses.cs.sfu.ca/grad/" + student.slug)
    for status, semester in list_of_status_semester_pairs:
        print("\t",status, semester)
    print("----------------------------------------------------------")
    

def graduated_students_who_are_not_graduated():
    results = []
    for student in cmpt_grad_students():
        statuses = GradStatus.objects.filter(student=student).order_by('start')
        lst = [status.status for status in statuses]
        pretty_lst = [(status.get_status_display(), status.start) for status in statuses] 
        try:
            if lst.index('GRAD') != len(lst)-1:
                print_student( student, pretty_lst )
                results.append( student )
        except ValueError:
            continue
    print(len(results))

def declined_offer_before_active_status():
    results = []
    for student in cmpt_grad_students():
        statuses = GradStatus.objects.filter(student=student).order_by('start')
        lst = [status.status for status in statuses]
        pretty_lst = [(status.get_status_display(), status.start) for status in statuses] 
        try:
            if 'ACTI' in lst and 'DECL' in lst and lst.index('ACTI') > lst.index('DECL'):
                print_student( student, pretty_lst )
                results.append( student )
        except ValueError:
            continue
    print(len(results))

def withdrawn_before_active_status():
    results = []
    for student in cmpt_grad_students():
        statuses = GradStatus.objects.filter(student=student).order_by('start')
        lst = [status.status for status in statuses]
        pretty_lst = [(status.get_status_display(), status.start) for status in statuses] 
        try:
            if 'ACTI' in lst and 'WIDR' in lst and lst.index('ACTI') > lst.index('WIDR'):
                print_student( student, pretty_lst )
                results.append( student )
        except ValueError:
            continue
    print(len(results))
