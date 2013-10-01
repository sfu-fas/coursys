"""
This is the script used to import engineering data from a CSV into 
our grad system. 

It requires a connection to the reporting database.

"""

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from coredata.models import Person, Unit, Role, Semester
from grad.models import GradStudent, GradProgram, Supervisor, GradStatus, GradRequirement, CompletedRequirement, GradProgramHistory

from new_grad_students import get_mother_tongue, get_passport_issued_by, holds_resident_visa 

import coredata.queries
from django.db import transaction

import datetime
import os
from cleaner.table import Table

from optparse import make_option

# When cleaning data, I used "UNK" for unknown/unparseable data ( 5-number student numbers, dates without years.. )
UNPARSEABLE = "UNK"
# Our data is full of _x000B_ characters, which I'm pretty sure are supposed to be newlines
NEWLINE = "_x000B_"

class Command(BaseCommand):
    """ Usage: 
        python manage.py engineering_import
    """
    args = '--input <csv_file> --unit ENG'
    help = 'Loads data from grad_data.csv into local DB'
        
    option_list = BaseCommand.option_list + (
            make_option('--input', action='store', type='string', dest='input'),
            make_option('--unit', action='store', type='string', dest='unit'),
            make_option('--unit_mech', action='store', type='string', dest='unit_mech'),
        )
    
    def handle(self, *args, **options):

        input_file = options['input']
        unit = Unit.objects.get(label=options['unit'])
        unit_mech = Unit.objects.get(label=options['unit_mech'])

        if not os.path.exists( input_file ):
            print input_file, " is not a valid file path. Please provide an --input x.csv argument."
            exit()

        table = Table.from_csv( input_file )

        fix_newlines( table )

        # programs 
        m_eng_program = find_or_generate_program( unit, "M.Eng.")
        m_asc_program = find_or_generate_program( unit, "M.A.Sc.")
        phd_program = find_or_generate_program( unit, "Ph.D.")
        special_program = find_or_generate_program( unit, "Special Non-Degree")
        
        m_eng_program_mech = find_or_generate_program( unit_mech, "M.Eng.")
        m_asc_program_mech = find_or_generate_program( unit_mech, "M.A.Sc.")
        phd_program_mech = find_or_generate_program( unit_mech, "Ph.D.")
        special_program_mech = find_or_generate_program( unit_mech, "Special Non-Degree")
        
        # requirements 
        # TODO : Create a milestone for Thesis Defense
        convocation = {}
        convocation[m_eng_program] = find_or_generate_requirement( m_eng_program, "Convocation ")
        convocation[m_asc_program] = find_or_generate_requirement( m_asc_program, "Convocation ")
        convocation[phd_program] = find_or_generate_requirement( phd_program, "Convocation ")
        convocation[special_program] = find_or_generate_requirement( special_program, "Convocation ")
        convocation[m_eng_program_mech] = find_or_generate_requirement( m_eng_program_mech, "Convocation ")
        convocation[m_asc_program_mech] = find_or_generate_requirement( m_asc_program_mech, "Convocation ")
        convocation[phd_program_mech] = find_or_generate_requirement( phd_program_mech, "Convocation ")
        convocation[special_program_mech] = find_or_generate_requirement( special_program_mech, "Convocation ")

        examining_committee_approval = {}
        examining_committee_approval[m_eng_program] = find_or_generate_requirement( m_eng_program, "Examining Committee Approval" )
        examining_committee_approval[m_asc_program] = find_or_generate_requirement( m_asc_program, "Examining Committee Approval" )
        examining_committee_approval[phd_program] = find_or_generate_requirement( phd_program, "Examining Committee Approval" )
        examining_committee_approval[special_program] = find_or_generate_requirement( special_program, "Examining Committee Approval" )
        examining_committee_approval[m_eng_program_mech] = find_or_generate_requirement( m_eng_program_mech, "Examining Committee Approval" )
        examining_committee_approval[m_asc_program_mech] = find_or_generate_requirement( m_asc_program_mech, "Examining Committee Approval" )
        examining_committee_approval[phd_program_mech] = find_or_generate_requirement( phd_program_mech, "Examining Committee Approval" )
        examining_committee_approval[special_program_mech] = find_or_generate_requirement( special_program_mech, "Examining Committee Approval" )

        supervisory_committee_approval = {}
        supervisory_committee_approval[m_eng_program] = find_or_generate_requirement( m_eng_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[m_asc_program] = find_or_generate_requirement( m_asc_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[phd_program] = find_or_generate_requirement( phd_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[special_program] = find_or_generate_requirement( special_program, "Supervisory Committee Approval" )
        supervisory_committee_approval[m_eng_program_mech] = find_or_generate_requirement( m_eng_program_mech, "Supervisory Committee Approval" )
        supervisory_committee_approval[m_asc_program_mech] = find_or_generate_requirement( m_asc_program_mech, "Supervisory Committee Approval" )
        supervisory_committee_approval[phd_program_mech] = find_or_generate_requirement( phd_program_mech, "Supervisory Committee Approval" )
        supervisory_committee_approval[special_program_mech] = find_or_generate_requirement( special_program_mech, "Supervisory Committee Approval" )
                                
        for row in table.row_maps():
            # Person
            student_number = row['Student Number']
            if student_number == "" or student_number == UNPARSEABLE:
                print row["Given Name(s)"] + " " + row["Surname"] + " doesn't have a student number and will not be imported." 
                continue
            person = find_or_generate_person( student_number )
            if person == None:
                print row["Given Name(s)"] + " throws an integrity error." 
                continue

            # Program
            degree = row['Degree'].lower().strip()
            research_area = row['Area of Research']
            if research_area.lower().strip() == "mechatronics":
                if degree in ["m.eng.", "m.eng"]:
                    program = m_eng_program_mech
                elif degree in ["ph.d.", "ph.d"]:
                    program = phd_program_mech
                elif degree in ['m.a.sc.', 'm.a.sc', 'masc']:
                    program = m_asc_program_mech
                elif degree in ['special non-degree', 'special nondegree']:
                    program = special_program_mech
                else: 
                    print row["Given Name(s)"] + " " + row["Surname"] + " program : " + degree + " not found." 
                    continue
            else:
                if degree in ["m.eng.", "m.eng"]:
                    program = m_eng_program
                elif degree in ["ph.d.", "ph.d"]:
                    program = m_asc_program
                elif degree in ['m.a.sc.', 'm.a.sc', 'masc']:
                    program = phd_program
                elif degree in ['special non-degree', 'special nondegree']:
                    program = special_program
                else: 
                    print row["Given Name(s)"] + " " + row["Surname"] + " program : " + degree + " not found." 
                    continue

            # Grad Student Fields
            english_fluency = row['TOEFL']

            mother_tongue = get_mother_tongue( student_number )
            passport_issued_by = get_passport_issued_by( student_number )
            if passport_issued_by == "Canada":
                is_canadian = True
            elif holds_resident_visa( student_number ):
                is_canadian = True
            else:
                is_canadian = False
            print mother_tongue, passport_issued_by, is_canadian

            mother_tongue = row['Native Language'] 
            comments = row['Comments']
            passport_issued_by = row['Passport']
            research_area = row['Area of Research']
            
            try:
                grad = GradStudent.objects.get( person=person )
                grad.english_fluency = english_fluency
                grad.mother_tongue = mother_tongue
                grad.is_canadian = is_canadian
                grad.comments = comments
                grad.passport_issued_by = passport_issued_by
                grad.research_area = research_area
            except GradStudent.DoesNotExist:
                grad = GradStudent( person=person,
                                    program=program,
                                    english_fluency=english_fluency, 
                                    mother_tongue=mother_tongue,
                                    is_canadian=is_canadian,
                                    research_area=research_area,
                                    passport_issued_by=passport_issued_by,
                                    comments=comments )
                print "Creating ", grad
                grad.save()

            assert(grad != None)

            # Statuses
            status = row['Status']  
            semester_left = row['Semester Left']
            semester_of_convocation = row['Convocation Semester']
            first_semester = row['First Semester']

            if status.lower().strip() == "graduated":
                find_or_generate_status( grad, 'ACTI', first_semester, semester_left )
                if semester_left != "":
                    find_or_generate_status( grad, 'GRAD', semester_left )
                elif semester_of_convocation != "":
                    find_or_generate_status( grad, 'GRAD', semester_of_convocation )
            elif status.lower().strip() == "withdrawn" or status.lower().strip() == "discontinued":
                find_or_generate_status( grad, 'ACTI', first_semester, semester_left )
                find_or_generate_status( grad, 'WIDR', semester_left )
            elif status.lower().strip() == "qualifying":
                print "Qualifying student. Status confusion!!! "
                continue
                # not sure
            elif status.lower().strip() == "deferred to next semester":
                # TODO: Not sure about this one.
                find_or_generate_status( grad, 'ACTI', first_semester )
            elif status.lower().strip() == "current" or status.lower().strip() == "new":
                find_or_generate_status( grad, 'ACTI', first_semester )
            else:
                print "Status " + status.lower().strip() + " not found. Error."
                continue
            
            # Semesters
            semester_of_approval_of_supervisory_committee = row['Semester of Approval of Supervisory Committee']
            find_or_generate_completed_requirement( grad, supervisory_committee_approval[program], semester_of_approval_of_supervisory_committee )

            semester_of_approval_of_examining_committee = row['Semester of Approval of Examining Committee']
            find_or_generate_completed_requirement( grad, examining_committee_approval[program], semester_of_approval_of_examining_committee )

            semester_of_convocation = row['Convocation Semester']
            find_or_generate_completed_requirement( grad, convocation[program], semester_of_convocation )

            grad.update_status_fields()
            print "Current Status: " + str(grad.current_status)

            # Visa
            person.config['visa'] = row['Visa Held']
            person.config['gender'] = row['Gender']
            person.config['citizen'] = row['Passport']
            person.save()

            grad.config['sin'] = row['Social Insurance Number']
            
            # Thesis Stuff 
            grad.config['work_title'] = row["Title of Thesis/Project"]

            thesis_date_set = row['Thesis Date'].split(',')
            if len(thesis_date_set) > 1:
                thesis_date_dirty = thesis_date_set[0]
                thesis_location = thesis_date_set[1]
                if thesis_location == UNPARSEABLE:
                    thesis_location = ""
                grad.config['thesis_location'] = thesis_location
                if thesis_date_dirty != UNPARSEABLE and thesis_date_dirty != "" and len(thesis_date_dirty) == 10:
                    thesis_date_clean = datetime.datetime.strptime(thesis_date_dirty, "%d-%m-%Y")
                    print thesis_date_clean
                    grad.config['exam_date'] = thesis_date_clean

            phd_qualifying_exam_set = row['PhD Qualifying Exam'].split(',')
            if len(phd_qualifying_exam_set) > 1:
                phd_exam_date_dirty = phd_qualifying_exam_set[0]
                phd_exam_location = phd_qualifying_exam_set[1]
                if phd_exam_location == UNPARSEABLE:
                    phd_exam_location = ""
                grad.config['qualifying_exam_location'] = phd_exam_location
                if phd_exam_date_dirty != UNPARSEABLE and phd_exam_date_dirty != "" and len(phd_exam_date_dirty) == 10:
                    phd_exam_date_clean = datetime.datetime.strptime( phd_exam_date_dirty, "%d-%m-%Y" )
                    print phd_exam_date_clean
                    grad.config['qualifying_exam_date'] = phd_exam_date_clean
            
            # Personal Details
            if row['Place of Birth'] != "":
                grad.config['place_of_birth'] = row['Place of Birth']
            if row['Bachelor CGPA'] != "":
                grad.config['bachelors_cgpa'] = row['Bachelor CGPA']
            if row['Master CGPA'] != "":
                grad.config['masters_cgpa'] = row['Master CGPA']
            
            grad.config['applic_email'] = row['Email']

            
            # Strings
            country = row['Country']
            birthday = row['Date of Birth']
            former_surname = row['Former Surname']
            
            # Dates
            progress = ""
            if row['M.Eng Progress'] != "" and len(row['M.Eng Progress']) == 10:
                progress = datetime.datetime.strptime( row['M.Eng Progress'], '%d-%m-%Y' )
            if row['PhD Progress'] != "" and len(row['PhD Progress']) == 10:
                progress = datetime.datetime.strptime( row['PhD Progress'], '%d-%m-%Y' )
            if row['MASc Progress'] != "" and len(row['MASc Progress']) == 10:
                progress = datetime.datetime.strptime( row['MASc Progress'], '%d-%m-%Y' )
            grad.config['progress'] = progress

            # Financial 
            president_stipend_research_award = row["President Stipend Research Award"]
            
            # Committee / Supervisors
            find_or_generate_supervisor(grad, 'SEN', row['Senior Supervisor'])
            find_or_generate_supervisor(grad, 'SEN', row['Senior Supervisor 2'])
            find_or_generate_supervisor(grad, 'COM', row['Supervisor 1'])
            find_or_generate_supervisor(grad, 'COM', row['Supervisory Committee 2'])
            find_or_generate_supervisor(grad, 'COM', row['Supervisory Committee 3'])
            find_or_generate_supervisor(grad, 'COM', row['Supervisory Committee 4'])
            find_or_generate_supervisor(grad, 'SFU', row['Internal Examiner'])
            find_or_generate_supervisor(grad, 'EXT', row['External Examiner'])
            find_or_generate_supervisor(grad, 'CHA', row['Chair'])

            grad.config['imported_from'] = 'Engineering Import Spring 2013'
            grad.save()
            
            start = find_or_generate_semester( first_semester )
            grad_program_history = GradProgramHistory(student=grad, program=program, start_semester=start)
            grad_program_history.save()

            print "-----------------------------------------------------"
            print " "

def fix_newlines( table ):
    # convert all "_x000B_" characters to newlines. 
    for row in table.rows:
        for i in xrange(0, len(row)):
            row[i] = row[i].replace(NEWLINE, "\n")

def find_or_generate_semester( name ):
    try: 
        semester = Semester.objects.get(name=name)
    except Semester.DoesNotExist:
        print "Semester " + name + " does not exist"
        # for the sake of the test system, we should generate these if they don't exist.
        # semester = Semester( name=name, start=datetime.date.today(), end=datetime.date.today() )
        # semester.save()
    return semester

def clean_semester( semester ):
    if semester == None:
        return None
    if len(semester) == 3:
        semester = "0" + semester
    if len(semester) != 4:
        print "Invalid Semester: " + semester
        return None
    return find_or_generate_semester( semester )


def find_or_generate_status( student, status, start, end=None ):
    start_semester = clean_semester( start )
    if start_semester == None:
        return None
    print status + " starting " + str(start_semester)

    end_semester = clean_semester( end )
    print status + " ending " + str(start_semester)

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
            print "Creating Supervisor: ", supervisor_type,  supervisor
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
        print "Creating Supervisor: ", supervisor_type,  supervisor
    return supervisor

def find_or_generate_program( unit, label ):
    try:
        return GradProgram.objects.get(unit=unit, label=label ) 
    except GradProgram.DoesNotExist:
        g = GradProgram( unit=unit, label=label, description=label) 
        print "Creating ", g 
        g.save()
        return g

def find_or_generate_requirement( program, description ):
    try:
        return GradRequirement.objects.get(program=program, description=description)
    except GradRequirement.DoesNotExist:
        g = GradRequirement( program=program, description=description )
        print "Creating ", g
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
        print "Creating ", c
        c.save()
        return c

def find_or_generate_person( emplid ):
    # return a Person object, either a student who exists in the system:
    try:
        p = Person.objects.get(emplid=emplid)
        print "Person " + str(p) + " found: " + str(p.id) 
        return p
    except Person.DoesNotExist:
        try:
            print "Fetching " + str(emplid) + " from SIMS" 
            p = coredata.queries.add_person( emplid )
            print str(p) + " fetched from SIMS"  
            return p
        except IntegrityError:
            print " Integrity error! " + str(emplid) + " 's userid already exists in the system." 
            return None
