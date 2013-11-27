
from grad.models import Scholarship, ScholarshipType
from ra.models import RAAppointment

# CS_GF and FAS_GF scholarships are being pulled in at $6000 rather than the correct $3000
# but only if there is an RA exceeding $3000 in the same semester


def in_same_semester( ra, scholarship ):
    try:
        return ra.semester_guess( ra.start_date ) == scholarship.start_semester
    except:
        return False

def fix():
    
    # for CS_GF or FAS_GF scholarships exceeding $6000, 
    # when a RA exceeding $2999.90 exists in the same semester
    # subtract $3000 from the total of the scholarship. 

    faulty_type = ["CS_GF", "FAS_GF"]
    s_type = ScholarshipType.objects.filter( name__in=faulty_type )
    scholarships = Scholarship.objects.filter( scholarship_type__in=s_type )

    to_fix = []
    to_ignore = []

    for scholarship in scholarships:
        ra_appointments_to_same_student = RAAppointment.objects.filter( person = scholarship.student.person )
        ra_appointments_in_same_semester = [ x for x in ra_appointments_to_same_student if in_same_semester( x, scholarship ) ]
        total_ra_payments = sum( [x.lump_sum_pay for x in ra_appointments_in_same_semester ] )

	if total_ra_payments > 2999: 
            to_fix.append( (scholarship, total_ra_payments) )
        else:
            to_ignore.append( (scholarship, total_ra_payments) )
    
    print "TO FIX "
    print "-------------------------"
    print "(emplid, name, scholarship, scholarship id, change, total_ra_payments)"
    for scholarship, total_ra_payments in to_fix:
        previous_amount = scholarship.amount
        if scholarship.amount > 5999:
            scholarship.amount = scholarship.amount - 3000
        print ( str(scholarship.student.person.emplid), 
                scholarship.student.person.name(),  
                scholarship, 
                scholarship.id, 
                "$" + str(previous_amount) + " changed to $" + str(scholarship.amount), 
                total_ra_payments)
    
    print " "
    print "TO IGNORE "
    print "-------------------------"
    for scholarship, total_ra_payments in to_ignore:
        print ( str(scholarship.student.person.emplid), 
                scholarship.student.person.name(),  
                scholarship, 
                scholarship.id, 
                "$" + str(scholarship.amount) + " ignored, no matching RA of value > $2999", 
                total_ra_payments )
