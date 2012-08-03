from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from coredata.models import Person, Unit, Role
import coredata.queries
import coredata.importer
from advisornotes.models import NonStudent, AdvisorNote
from django.db import transaction

import MySQLdb
import datetime

class Command(BaseCommand):
    """ Usage: 
        python manage.py load_data_from_intraweb --host <host> --port <port> --user <user> --password <password> 

    """
    args = '--host <hostname> --port <port> --user <user> --password <password> --unit FAS'
    help = 'Loads data from intraweb into local DB'
        
    option_list = BaseCommand.option_list + (
            make_option('--host', action='store', type='string', dest='host'),
            make_option('--port', action='store', type='int', dest='port'),
            make_option('--user', action='store', type='string', dest='user'),
            make_option('--password', action='store', type='string', dest='password'),
            make_option('--db', action='store', type='string', dest='db'),
            make_option('--unit', action='store', type='string', dest='unit')
        )

    def handle(self, *args, **options):
        
        print "Loading AMAINT user-ID mappings." 
        coredata.importer.update_amaint_userids()
        
        unit = Unit.objects.get(label=options['unit'])
        cursor = connect_and_cursor( options )

        non_students_by_id = non_student( unit, cursor ) 
        advisors( unit, cursor )
        notes( unit, cursor, non_students_by_id )

    
def connect_and_cursor(options):  
    connection = MySQLdb.connect( 
        host=options['host'], 
        port=options['port'], 
        user=options['user'], 
        passwd=options['password'], 
        db=options['db'] )

    return connection.cursor()

def non_student(unit, cursor):
    """
        Takes a Unit object ( the unit that all NonStudents will be added under
        and a MySQL cursor object.

        Adds all NonStudents that it can. 

        Returns a dictionary of NonStudent objects, keyed against their 'made-up' emplid
        from the original Advisor Data. We'll need this to attach the notes from the
        original system.
    """
    cursor.execute("""
                SELECT 
                    non.last_name,
                    non.first_name,
                    non.middle_name,
                    non.emplid,
                    non.address1,
                    non.address2,
                    non.city,
                    non.state,
                    non.country, 
                    non.postal,
                    non.phone,
                    non.sex,
                    non.email_addr
                FROM
                    non_csrpt_students non
                """)
    
    data = cursor.fetchall()

    existing_nonstudents = NonStudent.objects.all() 
    existing_nonstudent_hashes = [x.__hash__() for x in existing_nonstudents]
    
    non_students_by_imaginary_emplid = {}
    
    for row in data:
        try:
            last_name = row[0]
            first_name = row[1]
            middle_name = row[2]
            imaginary_emplid = row[3]

            if not last_name or not first_name:
                print "Not including " + str(first_name) + " " + str(last_name) + " - insufficient name." 
                continue

            note = " ".join( [unicode(i, "utf-8", errors='ignore') if i else "" for i in row[2:]] ) 
            newNonStudent = NonStudent( 
                first_name= first_name, 
                last_name= last_name, 
                middle_name= middle_name,
                high_school= "",
                notes=note,
                unit= unit ) 

            if newNonStudent.__hash__() in existing_nonstudent_hashes:
                print "Student "+newNonStudent.__repr__()+" already exists."
                non_students_by_imaginary_emplid[ imaginary_emplid ] = \
                    existing_nonstudents[ existing_nonstudent_hashes.index( newNonStudent.__hash__() ) ]
            else:
                newNonStudent.save()
                print "Student "+newNonStudent.__repr__()+" added." 
                non_students_by_imaginary_emplid[ imaginary_emplid ] = newNonStudent 
            
        except UnicodeDecodeError:
            print "Not including " + str(row[1]) + " " + str(row[0]) + " - Unicode Decode error."
        except:
            print "Not including " + str(row[1]) + " " + str(row[0]) + " - mysterious error."

    return non_students_by_imaginary_emplid

def notes( unit, cursor, non_students_by_imaginary_emplid ):
    cursor.execute("""
                SELECT
                    notes.student,
                    notes.notes,
                    notes.advisor,
                    notes.timestamp,
                    notes.attachment_URI,
                    notes.hide
                FROM 
                    notes
            """)
    
    data = cursor.fetchall()

    all_note_hashes = [x.__hash__() for x in AdvisorNote.objects.all() ]  
    
    for row in data:
        student_id = row[0]
        notes = row[1]
        advisor_userid = row[2]
        timestamp = row[3]
        attachment_uri = row[4]
        hide = row[5]
        
        if not student_id:
            print "No emplid? This note has no home." 
            continue

        print student_id, advisor_userid, hide
        student = find_or_generate_student( student_id, non_students_by_imaginary_emplid )
        if advisor_userid == 'margo':
            advisor = Person.objects.get(emplid=833060718)
        else:
            advisor = coredata.queries.get_person_by_userid( advisor_userid ) 

        if not student:
            print "Can't find student for this note."
            continue

        if not advisor:
            print "Advisor " + advisor_userid + " not found. Using dzhao."
            advisor = coredata.queries.get_person_by_userid( 'dzhao' )

        a = AdvisorNote(text=unicode(notes, 'latin-1'), advisor=advisor, created_at=timestamp , unit=unit )
        
        if type(student) == type( NonStudent() ):
            a.nonstudent = student
        else:
            a.student = student
        
        if attachment_uri: 
            a.file_attachment = "old/"+attachment_uri
            a.file_mediatype = "application/pdf" 

        if not a.__hash__() in all_note_hashes:
            print "Saving ", a
            a.save()
        else:
            print a, " already exists. "
            pass


def find_or_generate_student( emplid, non_students_by_imaginary_emplid ):
    # return a Person or NonPerson object, either a student who exists in the system:
    try:
        p = Person.objects.get(emplid=emplid)
        print "Person " + str(p) + " found." 
        return p
    except Person.DoesNotExist:
        try: 
            np = non_students_by_imaginary_emplid[emplid]
            print "NonPerson " + str(np) + " found"
            return np
        except KeyError:
            try:
                print "Fetching " + str(emplid) + " from SIMS" 
                p = coredata.queries.add_person( emplid )
                print str(p) + " fetched from SIMS"  
		return p
            except IntegrityError:
                print " Integrity error! " + str(emplid) + " 's userid already exists in the system." 
                return None


def advisors( unit, cursor ):
    """ Any advisors in the system should be advisors here. """ 
    cursor.execute("""
        SELECT DISTINCT
            notes.advisor
        FROM 
            notes """)
    
    data = cursor.fetchall()

    for row in data:
        advisor_userid = row[0]
	print "Importing advisor " + advisor_userid
        if advisor_userid == 'margo':
            p = coredata.queries.add_person(833060718)
        else:
            p = coredata.queries.get_person_by_userid( advisor_userid ) 
        if p:
	    r = Role.objects.filter(person=p,role="ADVS",unit=unit)
	    if len(r) == 0:
                r = Role(person=p, role="ADVS", unit=unit)
                r.save()
