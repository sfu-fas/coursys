from ..report import Report
from ..queries import SingleCourseQuery


class Mse410LessThan3Coops (Report):
        """
        Contact: Marilyn Trautman <mtrautma@sfu.ca>

        Here we are trying to gather students who have taken or are enrolled in MSE 410 but
        have less than 3 co-op terms, and at least 110 credits.

        The point of this is to try to avoid having people about to graduate who may try to finish
        with a Co-Op term, which is not allowed.
        """

        def run(self):
            # Queries
            students_in_mse_410_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '410'}, include_current=True)
            students_in_mse_410 = students_in_mse_410_query.result()

            # For now, let's assume that MSE 493 is Co-Op 3.  This has to be verified, though.
            students_in_mse_493_query = SingleCourseQuery({'subject': 'MSE', 'catalog_nbr': '493'}, include_current=True)
            students_in_mse_493 = students_in_mse_493_query.result()

            # We want to remove all people in 410 who have ever taken 493.
            emplid_in_493 = lambda x: students_in_mse_493.contains("EMPLID", x["EMPLID"])
            students_in_mse_410.filter(emplid_in_493)

