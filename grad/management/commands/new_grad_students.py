"""
Import new grad students from OASIS (SIMS).

It requires a connection to the reporting database.

"""

from django.core.management.base import BaseCommand, CommandError
from coredata.models import Person, Unit, Role, Semester
from grad.models import GradStudent, GradProgram, GradStatus, GradProgramHistory
from django.conf import settings

import coredata.queries
from django.db import transaction

import datetime
import os

from optparse import make_option

from django.conf import settings

grad_programs = {}
grad_programs['COMP SCI'] = ['CPPHD', 'CPPZU', 'CPMSC', 'CPMCW', 'CPMZU', 'CPGND', 'CPGQL', 'CPMBD']
grad_programs['ENG SCI'] = ['ESPHD', 'ESMAS', 'ESMEN']
grad_programs['MECH SYS'] = ['MSMAS', 'MSEPH', 'MSEMS'] 

class Command(BaseCommand):
    """ Usage: 
        python manage.py new_grad_students
    """
    args = '--semester 1134 --unit CMPT'
    help = 'Import new grad students from OASIS'
        
    option_list = BaseCommand.option_list + (
            make_option('--semester', action='store', type='string', dest='semester'),
            make_option('--unit', action='store', type='string', dest='unit'),
            make_option('--dryrun', action='store_true', default=False, dest='dryrun' ), #don't save anything.
            make_option('--skip_duplicates', action='store_true', default=False, dest='skip_duplicates'), #don't ask about possible duplicates
        )
    
    def handle(self, *args, **options):

        semester = options['semester']
        unit = Unit.objects.get(label=options['unit'])
        dryrun = options['dryrun']
        skip_duplicates = options['skip_duplicates'] 

        errors = []
        adm_appl_nbrs = []

        if settings.DEBUG:
            cmptunit = Unit.objects.get(label="COMP")
            program_map = {
                'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
                'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
                'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
                'CPMCW': GradProgram.objects.get(label="MSc Project", unit=cmptunit),
                'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
                'CPGND': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
                'CPGQL': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit)
            }
        else:
            cmptunit = Unit.objects.get(label="CMPT")
            mechunit = Unit.objects.get(label="MSE")
            enscunit = Unit.objects.get(label="ENSC")
            program_map = {
                'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
                'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
                'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
                'CPMCW': GradProgram.objects.get(label="MSc Course", unit=cmptunit),
                'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
                'CPGND': GradProgram.objects.get(label="Special", unit=cmptunit),
                'CPGQL': GradProgram.objects.get(label="Qualifying", unit=cmptunit),
                'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),

                'MSEPH': GradProgram.objects.get(label="Ph.D.", unit=mechunit),
                'MSEMS': GradProgram.objects.get(label="M.A.Sc.", unit=mechunit),
                'ESMAS': GradProgram.objects.get(label="M.A.Sc.", unit=enscunit),
                'ESMEN': GradProgram.objects.get(label="M.Eng.", unit=enscunit),
                'ESPHD': GradProgram.objects.get(label="Ph.D.", unit=enscunit)
            }

        if semester == None:
            print("You must provide a target semester (i.e. 1134) using the --semester argument.") 
            exit()

        semester_object = Semester.objects.get(name=semester)

        for emplid, adm_appl_nbr, acad_prog in get_grad_table(semester, grad_programs[unit.acad_org]): 
            errors, adm_appl_nbrs = import_student( program_map, semester_object, dryrun, skip_duplicates, unit, emplid, adm_appl_nbr, acad_prog, errors, adm_appl_nbrs )

        if len(errors) > 0:
            print("----------------------------------------")
            print("Errors: ")
            for error in errors:
                print(error)


def import_student( program_map, semester_object, dryrun, skip_duplicates, unit, emplid, adm_appl_nbr, acad_prog, errors, adm_appl_nbrs ):
    """
        program_map - a dictionary, mapping SIMS indicators ("CPPHD") to GradProgram objects (GradProgram.objects.get(...))
        semester - Semester
        dryrun - if True, do not actually import the student
        unit - Unit
        emplid - the emplid of the student to import 
        adm_appl_nbr - admission application number of the student to import
        acad_prog - acad_prog of the student to import
        errors - array containing any errors encountered by the system so far
        adm_appl_nbrs - array containing any adm_appl_nbrs encountered by the system so far. 
    """
    print(emplid, adm_appl_nbr)
    
    # Find or generate a Person object for this student
    person = find_or_generate_person(emplid)
    
    # Do we already have this student? 

    if is_already_imported( person, adm_appl_nbr ) or adm_appl_nbr in adm_appl_nbrs: 
        print("This GradStudent record already exists in coursys")
        print(" -------------------------------- ")
        return errors, adm_appl_nbrs
    
    # This additional check shouldn't be necessary, a year or so from now. 
    grad_student_records = GradStudent.objects.filter(person=person)
    
    if len(grad_student_records) > 0: 
        print("This GradStudent record may already exist in coursys: ")
        if skip_duplicates:
            print(".. so we're not dealing with it for now.") 
            return errors, adm_appl_nbrs
        else:
            print("Please select: ")
            for i in range(0, len(grad_student_records)):
                student = grad_student_records[i]
                print(i, "--", student, "--", "http://courses.cs.sfu.ca/grad/"+student.slug)
            print("N -- None of these are correct; Proceed with import.")
            n = get_number_or_n( list(range(0, len(grad_student_records))) )
            if n != 'n':
                correct_record = grad_student_records[n]
                correct_record.config['adm_appl_nbr'] = adm_appl_nbr
                if not dryrun:
                    correct_record.save()
                return errors, adm_appl_nbrs

    adm_appl_nbrs.append(adm_appl_nbr)

    # Find or generate a Program for this student
    try:
        program = program_map[acad_prog]
    except KeyError: 
        errors.append( emplid + " was not imported" )
        errors.append("\tThe program for " + acad_prog + " could not be found. This is a Bad Thing. Fix the program map.") 
        return errors, adm_appl_nbrs

    print(acad_prog)
    print(program)

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
    print(is_canadian)
    
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
    grad.config['adm_appl_nbr'] = adm_appl_nbr
    grad.config['imported_from'] = "Grad student import " + str(datetime.date.today())
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

    # GradProgramHistory
    history = GradProgramHistory(   student=grad, 
                                    program=program,
                                    start_semester=semester_object,
                                    starting=semester_object.start )
    
    # GradStatus 
    chronological_history = get_status_history( emplid, adm_appl_nbr)
    admitted = False
    grad_statuses = []
    for event, date, semester in chronological_history:
        status_code = None
        if event == "ADMT" or event == "COND":
            status_code = "OFFO"
            admitted = True
        elif event == "APPL":
            status_code = "COMP"
        elif event == "MATR":
            status_code = "CONF"
        elif event == "DENY":
            status_code = "REJE"
        elif event == "WAPP" or event == "WADM":
            if admitted:
                status_code = "DECL"
            else:
                status_code = "EXPI"
        else:
            print("Status " + event + " cannot be converted into a status.") 
            continue
        start_semester = Semester.objects.get(name=semester)
        status = GradStatus( student=grad, status=status_code, start=start_semester, start_date=date )
        print(status)
        grad_statuses.append( status )

    # Save all of the actual data. 
    if not dryrun:
        person.save()
        history.save() 
        for status in grad_statuses:
            status.save()

    print("------------------")
    return errors, adm_appl_nbrs


def get_number_or_n( valid_numbers ):
    response = input( "==> " )
    if response.strip().lower() != "n":
        try:
            response = int(response.strip())
            if not response in valid_numbers:
                print(response, "is not a valid number in this context.") 
                return get_number_or_n( valid_numbers )
            return response
        except ValueError:
            print(response, "could not be parsed as an integer.")
            return get_number_or_n( valid_numbers )
    else:
        return 'n'

def get_grad_table( semester, acad_progs ):

    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT DISTINCT prog.emplid, prog.adm_appl_nbr, prog.acad_prog
        FROM dbcsown.ps_adm_appl_prog prog
        LEFT JOIN dbcsown.ps_adm_appl_data data
            ON prog.adm_appl_nbr = data.adm_appl_nbr
        WHERE 
                prog.acad_prog IN %s             
                AND prog.prog_status NOT IN ('DC') 
            AND prog.admit_term = %s
            AND ( data.appl_fee_status in ('REC', 'WVD')
                  OR data.adm_appl_ctr in ('GRAW') )
    """, (acad_progs, semester) )
    return [(emplid, adm_appl_nbr, acad_prog) for emplid, adm_appl_nbr, acad_prog in db]

def get_status_history( emplid, adm_appl_nbr ):
    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT prog.prog_action, prog.action_dt, prog.admit_term
        FROM dbcsown.ps_adm_appl_prog prog
        WHERE 
            prog.emplid = %s
            AND prog.adm_appl_nbr = %s
            AND prog_action IN ('APPL', 'ADMT', 'COND', 'DENY', 'MATR', 'WAPP', 'WADM') 
        ORDER BY action_dt, prog_action
    """, (emplid, adm_appl_nbr) )
    return [(prog_action, action_dt, admit_term) for prog_action, action_dt, admit_term in db]

def get_mother_tongue( emplid ):
    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT atbl.descr
          FROM dbcsown.ps_accomplishments a,
               dbcsown.ps_accomp_tbl     atbl
         WHERE a.emplid=%s
           AND a.native_language='Y'
           AND a.accomplishment=atbl.accomplishment
           AND atbl.accomp_category='LNG'
        """, (emplid,) )
    for result in db:
        return result[0]

def get_passport_issued_by( emplid ):
    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT cou.descr 
        FROM dbcsown.ps_country_tbl cou
        INNER JOIN dbcsown.ps_citizenship cit 
            ON cit.country = cou.country
        WHERE cit.emplid = %s
        """, (emplid,) )
    for result in db:
        return result[0]

def holds_resident_visa( emplid ):
    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT *
        FROM ps_visa_permit_tbl tbl
        INNER JOIN ps_visa_pmt_data data
            ON tbl.visa_permit_type = data.visa_permit_type
        WHERE
            data.effdt = ( SELECT MAX(tmp.effdt) 
                                FROM dbcsown.ps_visa_pmt_data tmp
                                WHERE tmp.emplid = data.emplid
                                    AND tmp.effdt <= (SELECT current timestamp FROM sysibm.sysdummy1) )
            AND data.emplid = %s
            AND visa_permit_class = 'R'
        """, (emplid,) )
    # If there's at least one record with Permit Class TYPE R!, they are a resident
    for result in db:
        return True
    return False

def get_research_area( emplid, acad_org ):
    db = coredata.queries.SIMSConn()
    db.execute("""
        SELECT areas.descr50, choices.descr50
        FROM 
            dbcsown.ps_sfu_ga_res_det data
        INNER JOIN dbcsown.ps_sfu_ga_resareas areas
            ON data.sfu_ga_res_area = areas.sfu_ga_res_area
            AND areas.acad_org = %s
        INNER JOIN dbcsown.ps_sfu_ga_reschoic choices
            ON data.sfu_ga_reschoices = choices.sfu_ga_reschoices
            AND data.sfu_ga_res_area = areas.sfu_ga_res_area
            AND choices.sfu_ga_res_area = areas.sfu_ga_res_area
            AND areas.acad_org = %s
            AND choices.acad_org = %s
        WHERE 
            data.emplid = %s
        """, (acad_org, acad_org, acad_org, emplid) )
    choices = []
    for area, choice in db:
        if not choice in choices:
            choices.append(choice)
    return " | ".join(choices)


def is_already_imported( person, adm_appl_nbr ):
    """
    Check if there is a GradStudent record for this person containing
    the identifying adm_appl_nbr.
    """
    grads = GradStudent.objects.filter( person=person )
    for grad in grads:
        if 'adm_appl_nbr' in grad.config and grad.config['adm_appl_nbr'] == adm_appl_nbr:
            return True
    return False

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

def get_email( emplid ):
    # return the preferred e-mail if it exists for the person with emplid
    db = coredata.queries.SIMSConn()
    db.execute("""
    SELECT 
        email_addr
    FROM 
        ps_email_addresses
    WHERE 
        emplid = %s
        AND
        pref_email_flag = 'Y'
        """, (emplid,) )
    for email_address in db:
        return " ".join(email_address)
    return None
