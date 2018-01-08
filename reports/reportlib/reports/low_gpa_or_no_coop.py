from ..report import Report
from ..queries import ActiveProgramQuery, SingleCourseQuery, EmailQuery, NameQuery, CGPAQuery

class LowGPAOrNoCoOpReport(Report):
    """
    Contact:  Marilyn Trautman or Harriet Chicoine

    We are trying to get active students in engineering with more than 45 credits who meet either of these criteria:

    have not completed a co-op placement
    have a cgpa of less than 2.40
    """

    title = "Low GPA or no Co-Op report"
    description = "Returns a list of active engineering students with at least 45 credits and who have either" \
                  "not completed a single Co-Op term or have less than a 2.4 GPA"

    MIN_ALLOWABLE_CREDITS = 45
    MAX_ALLOWABLE_GPA = 2.40

    def run(self):

        #Queries

        # Get everyone in ENSC
        ensc_students_query = ActiveProgramQuery({'programs': ['ENSC']})
        ensc_students = ensc_students_query.result()

        # Get eveyone who has taken ENSC 195 and 196, since Harriet tells me that is Co-Op 1 for ENSC.
        students_in_ensc_195_query = SingleCourseQuery({'subject': 'ENSC', 'catalog_nbr': '195'}, include_current=True)
        students_in_ensc_195 = students_in_ensc_195_query.result()
        students_in_ensc_195_emplids = set(students_in_ensc_195.column_as_list('EMPLID'))

        students_in_ensc_196_query = SingleCourseQuery({'subject': 'ENSC', 'catalog_nbr': '196'}, include_current=True)
        students_in_ensc_196 = students_in_ensc_196_query.result()
        students_in_ensc_196_emplids = set(students_in_ensc_196.column_as_list('EMPLID'))
        
        students_in_mse_195_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '195'}, include_current=True)
        students_in_mse_195 = students_in_mse_195_query.result()
        students_in_mse_195_emplids = set(students_in_mse_195.column_as_list('EMPLID'))

        students_in_mse_196_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '196'}, include_current=True)
        students_in_mse_196 = students_in_mse_196_query.result()
        students_in_mse_196_emplids = set(students_in_mse_196.column_as_list('EMPLID'))


        # These are cached queries, so it shouldn't be *too* expensive to run them.
        # see bad_first_semester.py

        email_query = EmailQuery()
        email = email_query.result()
        email.filter(EmailQuery.campus_email)

        name_query = NameQuery()
        names = name_query.result()

        gpa_query = CGPAQuery()
        gpas = gpa_query.result()

        ensc_students.left_join(names, "EMPLID")
        ensc_students.left_join(email, "EMPLID")
        ensc_students.left_join(gpas, "EMPLID")

        # Filter out people who don't have 45 credits yet.
        def too_few_credits(row_map):
            try:
                return float(row_map["CREDITS"]) > LowGPAOrNoCoOpReport.MIN_ALLOWABLE_CREDITS
            except ValueError:
                print("Could not convert credit value to float")

        ensc_students.filter(too_few_credits)
        ensc_students.compute_column('AT_LEAST_ONE_CO_OP', lambda x: x['EMPLID'] in students_in_ensc_195_emplids
                                     or x['EMPLID'] in students_in_ensc_196_emplids
                                     or x['EMPLID'] in students_in_mse_195_emplids
                                     or x['EMPLID'] in students_in_mse_196_emplids)

        # Remove people with too high a GPA who have taken at least one Co-Op term.  That should
        # leave us only the ones we want to address.
        def no_coop_or_low_gpa(row_map):
            try:
                if float(row_map["CUM_GPA"]) >= LowGPAOrNoCoOpReport.MAX_ALLOWABLE_GPA:
                    return not row_map["AT_LEAST_ONE_CO_OP"]
                else:
                    return True
            except ValueError:
                print("Could not convert GPA to float")

        ensc_students.filter(no_coop_or_low_gpa)

        # Output
        self.artifacts.append(ensc_students)

