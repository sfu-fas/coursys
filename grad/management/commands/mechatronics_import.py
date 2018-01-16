"""
Import Mechatronics Grad Students

It requires a connection to the reporting database.

"""

from django.core.management.base import BaseCommand, CommandError
from coredata.models import Person, Unit, Role, Semester
from grad.models import GradStudent, GradProgram, GradStatus, GradProgramHistory
from django.conf import settings
from .new_grad_students import * 

import coredata.queries
from django.db import transaction

import datetime
import os

from optparse import make_option

from django.conf import settings

class Command(BaseCommand):
    """ Usage: 
        python manage.py mechatronics_import
    """
    args = ''
    help = 'Import existing grad students'
        
    option_list = BaseCommand.option_list + ()
    
    def handle(self, *args, **options):

        unit = Unit.objects.get(label='MSE')
        program_map = {
            'MSEPH': GradProgram.objects.get(label="Ph.D.", unit=unit),
            'MSEMS': GradProgram.objects.get(label="M.A.Sc.", unit=unit),
        }

        import_tuples = [
            ('301038983', 'MSEMS', '1127'),
            ('301068709', 'MSEMS', '1131'),
            ('301072349', 'MSEMS', '1127'),
            ('301073001', 'MSEMS', '1127'),
            ('301080623', 'MSEMS', '1137'),
            ('301086441', 'MSEMS', '1127'),
            ('301099830', 'MSEMS', '1137'),
            ('301119523', 'MSEMS', '1101'),
            ('301129768', 'MSEMS', '1121'),
            ('301133170', 'MSEMS', '1141'),
            ('301158230', 'MSEMS', '1111'),
            ('301167724', 'MSEMS', '1117'),
            ('301168717', 'MSEMS', '1117'),
            ('301185090', 'MSEMS', '1121'),
            ('301191318', 'MSEMS', '1127'),
            ('301192216', 'MSEMS', '1124'),
            ('301193069', 'MSEMS', '1127'),
            ('301196799', 'MSEMS', '1127'),
            ('301197265', 'MSEMS', '1127'),
            ('301197841', 'MSEMS', '1137'),
            ('301200844', 'MSEMS', '1127'),
            ('301201301', 'MSEMS', '1131'),
            ('301201544', 'MSEMS', '1134'),
            ('301204525', 'MSEMS', '1127'),
            ('301213248', 'MSEMS', '1127'),
            ('301213719', 'MSEMS', '1137'),
            ('301215993', 'MSEMS', '1137'),
            ('301216374', 'MSEMS', '1134'),
            ('301216810', 'MSEMS', '1134'),
            ('301218121', 'MSEMS', '1131'),
            ('301222981', 'MSEMS', '1141'),
            ('301224434', 'MSEMS', '1137'),
            ('301228398', 'MSEMS', '1137'),
            ('301230016', 'MSEMS', '1137'),
            ('301241424', 'MSEMS', '1141'),
            ('301070428', 'MSEPH', '1087'),
            ('301072778', 'MSEPH', '1097'),
            ('301074316', 'MSEPH', '1107'),
            ('301078978', 'MSEPH', '1114'),
            ('301087831', 'MSEPH', '1087'),
            ('301089485', 'MSEPH', '1104'),
            ('301093615', 'MSEPH', '1131'),
            ('301096503', 'MSEPH', '1084'),
            ('301097717', 'MSEPH', '1097'),
            ('301108351', 'MSEPH', '1097'),
            ('301109542', 'MSEPH', '1094'),
            ('301115334', 'MSEPH', '1104'),
            ('301115911', 'MSEPH', '1097'),
            ('301117586', 'MSEPH', '1101'),
            ('301119073', 'MSEPH', '1097'),
            ('301120095', 'MSEPH', '1117'),
            ('301132563', 'MSEPH', '1104'),
            ('301132847', 'MSEPH', '1111'),
            ('301132961', 'MSEPH', '1137'),
            ('301135127', 'MSEPH', '1141'),
            ('301135788', 'MSEPH', '1107'),
            ('301137480', 'MSEPH', '1124'),
            ('301137803', 'MSEPH', '1104'),
            ('301141421', 'MSEPH', '1107'),
            ('301142165', 'MSEPH', '1107'),
            ('301143207', 'MSEPH', '1131'),
            ('301144628', 'MSEPH', '1107'),
            ('301145054', 'MSEPH', '1117'),
            ('301154403', 'MSEPH', '1134'),
            ('301154664', 'MSEPH', '1111'),
            ('301156822', 'MSEPH', '1111'),
            ('301156886', 'MSEPH', '1111'),
            ('301157173', 'MSEPH', '1107'),
            ('301157267', 'MSEPH', '1134'),
            ('301158700', 'MSEPH', '1117'),
            ('301158891', 'MSEPH', '1114'),
            ('301159057', 'MSEPH', '1117'),
            ('301160549', 'MSEPH', '1114'),
            ('301161534', 'MSEPH', '1117'),
            ('301165973', 'MSEPH', '1121'),
            ('301170303', 'MSEPH', '1121'),
            ('301171445', 'MSEPH', '1141'),
            ('301182192', 'MSEPH', '1117'),
            ('301182949', 'MSEPH', '1121'),
            ('301184893', 'MSEPH', '1117'),
            ('301185104', 'MSEPH', '1121'),
            ('301185953', 'MSEPH', '1137'),
            ('301185958', 'MSEPH', '1121'),
            ('301186779', 'MSEPH', '1121'),
            ('301197177', 'MSEPH', '1131'),
            ('301198229', 'MSEPH', '1127'),
            ('301208764', 'MSEPH', '1127'),
            ('301213862', 'MSEPH', '1131'),
            ('301214291', 'MSEPH', '1137'),
            ('301216009', 'MSEPH', '1134'),
            ('301217167', 'MSEPH', '1137'),
            ('301230279', 'MSEPH', '1137'),
            ('301238443', 'MSEPH', '1141'),
            ('301241798', 'MSEPH', '1141'),
            ('301241809', 'MSEPH', '1137')
        ]

        for import_tuple in import_tuples:
            import_student( emplid=import_tuple[0], 
                            gradprogram=program_map[import_tuple[1]],
                            semester_string=import_tuple[2], 
                            dryrun=False )


def import_student( emplid, gradprogram, semester_string, dryrun=True ):
    """
        Import student with emplid into gradprogram, using as much SIMS data as possible. 
    """
    person = find_or_generate_person(emplid)
    program = gradprogram
    print(person, program)
    
    english_fluency = ""
    mother_tongue = get_mother_tongue( emplid )
    print(mother_tongue)

    passport_issued_by = get_passport_issued_by( emplid )
    print(passport_issued_by)

    if passport_issued_by == "Canada":
        is_canadian = True
    elif holds_resident_visa( emplid ):
        is_canadian = True
    else:
        is_canadian = False
    print("Canadian: ", is_canadian)
    
    research_area = get_research_area( emplid, program.unit.acad_org )
    print(research_area)

    grad = GradStudent( person=person,
                        program=program,
                        english_fluency=english_fluency, 
                        mother_tongue=mother_tongue,
                        is_canadian=is_canadian,
                        research_area=research_area,
                        passport_issued_by=passport_issued_by,
                        comments="" )
    grad.config['imported_from'] = "MSE special import " + str(datetime.date.today())
    email = get_email(emplid)
    if email:
        grad.config['applic_email'] = email
    print("Creating new Grad Student")
    print(grad)

    if not dryrun:
        grad.save()
    
    # Personal data 
    personal_info = coredata.queries.grad_student_info(emplid) 
    print(personal_info)
    if 'visa' in personal_info:
        person.config['visa'] = personal_info['visa']
    if 'citizen' in personal_info:
        person.config['citizen'] = personal_info['citizen']
    if 'ccredits' in personal_info:
        person.config['ccredits'] = personal_info['ccredits']
    if 'gpa' in personal_info:
        person.config['gpa'] = personal_info['gpa']
    if 'gender' in personal_info:
        person.config['gender'] = personal_info['gender']

    try: 
        semester_object = Semester.objects.get(name=semester_string)
    except Semester.DoesNotExist:
        print("Semester " + name + " does not exist")
        return

    # GradProgramHistory
    history = GradProgramHistory(   student=grad, 
                                    program=program,
                                    start_semester=semester_object,
                                    starting=semester_object.start )
    print(history)
  
    status = GradStatus(student=grad, status='ACTI', start=semester_object)
    print(status)

    # Save all of the actual data. 
    if not dryrun:
        person.save()
        history.save() 
        status.save()

    print("------------------")


