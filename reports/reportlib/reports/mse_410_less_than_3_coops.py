from ..report import Report
from ..queries import SingleCourseStrmQuery, StudentsTotalCreditsQuery, GraduatedStudentQuery, NameQuery, EmailQuery


class Mse410LessThan3CoopsReport (Report):
        """
        Contact: Marilyn Trautman <mtrautma@sfu.ca>

        Here we are trying to gather students who have taken or are enrolled in MSE 410 but
        have less than 3 co-op terms, and at least 110 credits.

        The point of this is to try to avoid having people about to graduate who may try to finish
        with a Co-Op term, which is not allowed.
        """

        title = "MSE 410 With Less than 3 Co-Op terms and more than 110 credits"
        description = "Returns a list of students who have taken MSE 410, but who haven't done 3 co-op terms yet " \
                      "and have more than 110 credits, so they risk attempting to graduate soon."
        MAX_ALLOWABLE_CREDITS = 110

        def run(self):

            # Queries
            students_in_mse_410_query = SingleCourseStrmQuery({'subject': 'MSE', 'catalog_nbr': '410'},
                                                              include_current=True)
            students_in_mse_410 = students_in_mse_410_query.result()

            # For now, let's assume that MSE 493 is Co-Op 3.  This has to be verified, though.
            students_in_mse_493_query = SingleCourseStrmQuery({'subject': 'MSE', 'catalog_nbr': '493'},
                                                              include_current=True)
            students_in_mse_493 = students_in_mse_493_query.result()

            # After revision, we need to also remove students who have taken MSE 494
            students_in_mse_494_query = SingleCourseStrmQuery({'subject': 'MSE', 'catalog_nbr': '494'},
                                                              include_current=True)

            students_in_mse_494 = students_in_mse_494_query.result()

            students_in_ensc_395_query = SingleCourseStrmQuery({'subject': 'ENSC', 'catalog_nbr': '395'},
                                                         include_current=True)

            students_in_ensc_395 = students_in_ensc_395_query.result()

            # These are cached queries, so it shouldn't be *too* expensive to run them.
            # see bad_first_semester.py

            email_query = EmailQuery()
            email = email_query.result()
            email.filter( EmailQuery.campus_email )

            name_query = NameQuery()
            names = name_query.result()

            students_in_mse_410.left_join( names, "EMPLID" )
            students_in_mse_410.left_join( email, "EMPLID" )
            # Filters
            def too_few_credits(row_map):
                try:
                    return float(row_map["CREDITS"]) > Mse410LessThan3CoopsReport.MAX_ALLOWABLE_CREDITS
                except ValueError:
                    print("Could not convert credit value to float")

            def did_3_coops(row_map):
                try:
                    return not (students_in_mse_493.contains("EMPLID", row_map["EMPLID"]) or
                                students_in_mse_494.contains("EMPLID", row_map["EMPLID"]) or
                                students_in_ensc_395.contains("EMPLID", row_map["EMPLID"]))
                except KeyError:
                    print("No emplid in the given row.")

            def graduated(row_map):
                try:
                    return not students_graduated.contains("EMPLID", row_map["EMPLID"])
                except KeyError:
                    print("No emplid in the given row.")

            # We want to remove all people in 410 who have ever taken 493 or 494.
            students_in_mse_410.filter(did_3_coops)

            # For those who are left now, let's fetch their total cumulative credits
            # and weed out the ones who have too few to worry about.

            emplids = students_in_mse_410.column_as_list("EMPLID")
            students_credits_query = StudentsTotalCreditsQuery({'emplids': emplids})
            student_credits = students_credits_query.result()
            students_in_mse_410.left_join(student_credits, "EMPLID")
            students_in_mse_410.filter(too_few_credits)

            # Let's check those remaining students for graduations.  MSE 410 only started getting offered in semester
            # 1141.
            # Also, we're going to have to make some assumptions here.  If you completed an academic program for ENG,
            # MSE, or MSE2, we're going to assume you're not doing another MSE degree.
            emplids = students_in_mse_410.column_as_list("EMPLID")
            students_graduated_query = GraduatedStudentQuery({'emplids': emplids, 'programs': ['ENSC', 'ENSC2', 'ENBUX', 'ENG', 'MSE', 'MSE2'],
                                                              'start_semester': '1141'})
            students_graduated = students_graduated_query.result()

            students_in_mse_410.filter(graduated)

            # The final output
            self.artifacts.append(students_in_mse_410)
