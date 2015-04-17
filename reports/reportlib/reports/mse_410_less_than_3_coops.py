from ..report import Report
from ..queries import SingleCourseQuery, StudentsTotalCreditsQuery


class Mse410LessThan3CoopsReport (Report):
        """
        Contact: Marilyn Trautman <mtrautma@sfu.ca>

        Here we are trying to gather students who have taken or are enrolled in MSE 410 but
        have less than 3 co-op terms, and at least 110 credits.

        The point of this is to try to avoid having people about to graduate who may try to finish
        with a Co-Op term, which is not allowed.
        """

        # TODO:  Still need to eliminate the graduates, and change the first query to return the matching smstr.

        title = "MSE 410 With Less than 3 Co-Op terms"
        description = "Returns a list of students who have taken MSE 410, but who haven't done 3 co-op terms yet " \
                      "and have more than 110 credits, so they risk attempting to graduate soon."
        MAX_ALLOWABLE_CREDITS = 110

        def run(self):

            # Queries
            students_in_mse_410_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '410'}, include_current=True)
            students_in_mse_410 = students_in_mse_410_query.result()

            # For now, let's assume that MSE 493 is Co-Op 3.  This has to be verified, though.
            students_in_mse_493_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '493'}, include_current=True)
            students_in_mse_493 = students_in_mse_493_query.result()

            # Filters
            def too_few_credits(row_map):
                try:
                    return float(row_map["CREDITS"]) > Mse410LessThan3CoopsReport.MAX_ALLOWABLE_CREDITS
                except ValueError:
                    print "Could not convert credit value to float"

            def did_3_coops(row_map):
                try:
                    return students_in_mse_493.contains("EMPLID", row_map["EMPLID"])
                except KeyError:
                    print "No emplid in the given row."

            # We want to remove all people in 410 who have ever taken 493.
            students_in_mse_410.filter(did_3_coops)

            # For those who are left now, let's fetch their total cumulative credits
            # and weed out the ones who have too few to worry about.

            emplids = students_in_mse_410.column_as_list("EMPLID")
            students_credits_query = StudentsTotalCreditsQuery({'emplids': emplids})
            credits = students_credits_query.result()
            students_in_mse_410.left_join(credits, "EMPLID")
            students_in_mse_410.filter(too_few_credits)

            #The final output
            self.artifacts.append(students_in_mse_410)
