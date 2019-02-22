"""
This is the script used to import engineering data from a CSV into 
our grad system. 

It requires a connection to the reporting database.

"""

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from coredata.models import Person, Unit, Role, Semester
from grad.models import *
from grad.importer import create_or_update_student

from .new_grad_students import get_mother_tongue, get_passport_issued_by, holds_resident_visa 

import coredata.queries
from django.db import transaction

import datetime
import os
from .cleaner.table import Table

from optparse import make_option

# When cleaning data, I used "UNK" for unknown/unparseable data ( 5-number student numbers, dates without years.. )
UNPARSEABLE = "UNK"
# Our data is full of _x000B_ characters, which I'm pretty sure are supposed to be newlines
NEWLINE = "_x000B_"

def datetidy( datestring ):
    try:
        return datetime.datetime.strptime( datestring, "%d-%m-%Y" )
    except ValueError:
        try:
            return datetime.datetime.strptime( datestring, "%m-%d-%Y" )
        except ValueError:
            return None

class Command(BaseCommand):
    """ Usage: 
        python manage.py engineering_import
    """
    args = '--input <csv_file> --unit ENG'
    help = 'Loads data from grad_data.csv into local DB'
        
    option_list = BaseCommand.option_list + (
            make_option('--input', action='store', type='string', dest='input'),
            make_option('--unit', action='store', type='string', dest='unit'),
        )
    
    def handle(self, *args, **options):

        input_file = options['input']
        unit = Unit.objects.get(label=options['unit'])

        if not os.path.exists( input_file ):
            print(input_file, " is not a valid file path. Please provide an --input x.csv argument.")
            exit()

        table = Table.from_csv( input_file )

        fix_newlines( table )

        # programs 
        m_eng_program = find_or_generate_program( unit, "M.Eng.")
        m_asc_program = find_or_generate_program( unit, "M.A.Sc.")
        phd_program = find_or_generate_program( unit, "Ph.D.")
        
        # requirements 
        # TODO : Create a milestone for Thesis Defense
        convocation = {}
        convocation[m_eng_program] = find_or_generate_requirement( m_eng_program, "Convocation ")
        convocation[m_asc_program] = find_or_generate_requirement( m_asc_program, "Convocation ")
        convocation[phd_program] = find_or_generate_requirement( phd_program, "Convocation ")

        examining_committee_approval = {}
        examining_committee_approval[m_eng_program] = find_or_generate_requirement( m_eng_program, "Examining Committee Approval" )
        examining_committee_approval[m_asc_program] = find_or_generate_requirement( m_asc_program, "Examining Committee Approval" )
        examining_committee_approval[phd_program] = find_or_generate_requirement( phd_program, "Examining Committee Approval" )

        supervisory_committee_approval = {}
        supervisory_committee_approval[m_eng_program] = find_or_generate_requirement( m_eng_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[m_asc_program] = find_or_generate_requirement( m_asc_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[phd_program] = find_or_generate_requirement( phd_program, "Supervisory Committee Approval" )
            
        for row in table.row_maps():
            # Person
            student_number = row['SFU ID']
            if student_number == "" or student_number == UNPARSEABLE:
                print(row["FIRST NAME"] + " " + row["SURNAME"] + " doesn't have a student number and will not be imported.") 
                continue

            create_or_update_student( student_number )

            # Program
            degree = row['PROGRAM'].lower().strip()
            research_area = row['AREA OF RESEARCH ']
            if research_area.lower().strip() == "mechatronics":
                continue
            else:
                if degree in ["m.eng.", "m.eng"]:
                    program = m_eng_program
                elif degree in ["ph.d.", "ph.d"]:
                    program = phd_program
                elif degree in ['m.a.sc.', 'm.a.sc', 'masc']:
                    program = m_asc_program
                else: 
                    print(row["FIRST NAME"] + " " + row["SURNAME"] + " program : " + degree + " not found.") 
                    continue

            gradstudent_records = GradStudent.objects.filter(person__emplid=student_number, program=program)

            if len(gradstudent_records) > 1:
                print("Too many grad student records!") 
            if len(gradstudent_records) > 0:
                grad = gradstudent_records[0]
            else:
                print("Grad Student not created")
                continue
            
            # Semesters
            semester_of_approval_of_supervisory_committee = row['SEMESTER OF APPROVAL OF SUPERVISORY COMMITTEE']
            find_or_generate_completed_requirement( grad, supervisory_committee_approval[program], semester_of_approval_of_supervisory_committee )

            semester_of_approval_of_examining_committee = row['SEMESTER OF APPROVAL OF EXAMINING COMMITTEE']
            find_or_generate_completed_requirement( grad, examining_committee_approval[program], semester_of_approval_of_examining_committee )

            semester_of_convocation = row['CONVOCATION SEMESTER']
            find_or_generate_completed_requirement( grad, convocation[program], semester_of_convocation )

            # Thesis Stuff 
            grad.config['work_title'] = row["THESIS TITLE"]

            thesis_date_set = row['THESIS DATE'].split(',')
            if len(thesis_date_set) > 1:
                thesis_date_dirty = thesis_date_set[0]
                thesis_location = thesis_date_set[1]
                if thesis_location == UNPARSEABLE:
                    thesis_location = ""
                grad.config['thesis_location'] = thesis_location
                if thesis_date_dirty != UNPARSEABLE and thesis_date_dirty != "" and len(thesis_date_dirty) == 10:
                    thesis_date_clean = datetidy(thesis_date_dirty)
                    if thesis_date_clean:
                        print(thesis_date_clean)
                        grad.config['exam_date'] = thesis_date_clean

            phd_qualifying_exam_set = row['PHD QUALIFYING EXAM'].split(',')
            if len(phd_qualifying_exam_set) > 1:
                phd_exam_date_dirty = phd_qualifying_exam_set[0]
                phd_exam_location = phd_qualifying_exam_set[1]
                if phd_exam_location == UNPARSEABLE:
                    phd_exam_location = ""
                grad.config['qualifying_exam_location'] = phd_exam_location
                if phd_exam_date_dirty != UNPARSEABLE and phd_exam_date_dirty != "" and len(phd_exam_date_dirty) == 10:
                    phd_exam_date_clean = datetidy(phd_exam_date_dirty)
                    if phd_exam_date_clean:
                        print(phd_exam_date_clean)
                        grad.config['qualifying_exam_date'] = phd_exam_date_clean
            
            # Dates
            progress = ""
            if row['M.ENG. PROGRESS'] != "" and len(row['M.ENG. PROGRESS']) == 10:
                progress = datetime.datetime.strptime( row['M.ENG. PROGRESS'], '%d-%m-%Y' )
            if row['PH.D. PROGRESS'] != "" and len(row['PH.D. PROGRESS']) == 10:
                progress = datetime.datetime.strptime( row['PH.D. PROGRESS'], '%d-%m-%Y' )
            if row['M.A.SC. PROGRESS'] != "" and len(row['M.A.SC. PROGRESS']) == 10:
                progress = datetime.datetime.strptime( row['M.A.SC. PROGRESS'], '%d-%m-%Y' )
            grad.config['progress'] = progress

            grad.config['imported_from'] = 'Engineering Import Winter 2013'
            grad.save()

            print("-----------------------------------------------------")
            print(" ")

def fix_newlines( table ):
    # convert all "_x000B_" characters to newlines. 
    for row in table.rows:
        for i in range(0, len(row)):
            row[i] = row[i].replace(NEWLINE, "\n")

def clean_semester( semester ):
    if semester == None:
        return None
    if len(semester) == 3:
        semester = "0" + semester
    if len(semester) != 4:
        print("Invalid Semester: " + semester)
        return None
    try:
        return Semester.objects.get(name=semester)
    except Semester.DoesNotExist:
        return None

def find_or_generate_status( student, status, start, end=None ):
    start_semester = clean_semester( start )
    if start_semester == None:
        return None
    print(status + " starting " + str(start_semester))

    end_semester = clean_semester( end )
    print(status + " ending " + str(start_semester))

    try:
        status = GradStatus.objects.get( student=student, 
                                        status=status,
                                        start=start_semester)
    except GradStatus.DoesNotExist:
        status = GradStatus( student=student, status=status, start=start_semester )
        if end_semester != None:
            status.end = end_semester
        status.save()
    return status


def find_or_generate_supervisor( student, supervisor_type, data ):
    """ Find or generate a supervisor for student <Student Object>,
        with supervisor_type (i.e. "SEN", "COM", "SFU", see grad.models )
        using the data in "data"
    """
    # data is None/null/UNK
    cleaned_data = data.lower().strip()
    if data == None or cleaned_data == "" or cleaned_data == UNPARSEABLE:
        return None

    # data is 999999999
    if len(cleaned_data) == 9 and cleaned_data.isdigit():
        person = find_or_generate_person( cleaned_data )
        if person == None:
            return None
        try: 
            supervisor = Supervisor.objects.get( student=student, 
                                                supervisor_type=supervisor_type, 
                                                supervisor=person )  
        except Supervisor.DoesNotExist: 
            supervisor = Supervisor( student=student, 
                                    supervisor_type=supervisor_type, 
                                    supervisor=person )
            print("Creating Supervisor: ", supervisor_type,  supervisor)
            supervisor.save()
        return supervisor

    # data is 999999999,<something>
    if len(cleaned_data) > 10 and cleaned_data[0:9].isdigit() and cleaned_data[10] == ",":
        return [ find_or_generate_supervisor( student, supervisor_type, cleaned_data[0:9] ),
                 find_or_generate_supervisor( student, supervisor_type, cleaned_data[10:] ) ]

    # data is string
    try: 
        supervisor = Supervisor.objects.get( student=student, supervisor_type=supervisor_type, external=data )
    except Supervisor.DoesNotExist:
        supervisor = Supervisor( student=student, supervisor_type=supervisor_type, external=data )
        supervisor.save()
        print("Creating Supervisor: ", supervisor_type,  supervisor)
    return supervisor

def find_or_generate_program( unit, label ):
    try:
        return GradProgram.objects.get(unit=unit, label=label ) 
    except GradProgram.DoesNotExist:
        g = GradProgram( unit=unit, label=label, description=label) 
        print("Creating ", g) 
        g.save()
        return g

def find_or_generate_requirement( program, description ):
    try:
        return GradRequirement.objects.get(program=program, description=description)
    except GradRequirement.DoesNotExist:
        g = GradRequirement( program=program, description=description )
        print("Creating ", g)
        g.save()
        return g

def find_or_generate_completed_requirement( student, requirement, semester ):
    semester = clean_semester(semester)
    if semester == None:
        return None
    try: 
        return CompletedRequirement.objects.get( student=student, 
                                                 requirement=requirement,
                                                 semester=semester ) 
    except CompletedRequirement.DoesNotExist:
        c = CompletedRequirement( student=student,
                                  requirement=requirement,
                                  semester=semester )
        print("Creating ", c)
        c.save()
        return c

def find_or_generate_person( emplid ):
    # return a Person object, either a student who exists in the system:
    try:
        p = Person.objects.get(emplid=emplid)
        print("Person " + str(p) + " found: " + str(p.id)) 
        return p
    except Person.DoesNotExist:
        try:
            print("Fetching " + str(emplid) + " from SIMS") 
            p = coredata.queries.add_person( emplid )
            print(str(p) + " fetched from SIMS")  
            return p
        except IntegrityError:
            print(" Integrity error! " + str(emplid) + " 's userid already exists in the system.") 
            return None
