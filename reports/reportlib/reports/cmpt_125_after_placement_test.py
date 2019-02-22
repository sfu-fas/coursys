from ..report import Report
from ..queries import SingleCourseStrmGradeQuery, NameQuery, EmailQuery


class CMPT125AfterPlacementTestReport (Report):
    title = "CMPT 125 Grade After Placement Test"
    description = "In order to evaluate the effectiveness of the CMPT 120 Placement Test, we are " \
                  "checking the CMPT 125 grades of the people who passed the Placement Test."

    def run(self):
        from onlineforms.models import SheetSubmission
        # This entire report is very un-robust.  We have to basically check which choice was filled in the results
        # sheet.  If any of these choices or slugs ever change, this report will be useless.  We are relying on
        # slug names to even get the right SheetSubmissions

        # Let's get all the results sheet submissions for completed placement tests.
        ss = SheetSubmission.objects.filter(sheet__form__slug='cmpt-cmpt-120-placement-test', status='DONE',
                                            sheet__slug='results')
        passed_students_emplids = set()
        # Let's just check every sheet submission to see if the first field has the second choice picked.  Once
        # again, if any of this changes in the form, this report is hooped.
        for s in ss:
            if 'info' in s.field_submissions[0].data and s.field_submissions[0].data['info'] == 'choice_2':
                passed_students_emplids.add(str(s.form_submission.initiator.emplid()))

        passed_students_emplids = list(passed_students_emplids)
        cmpt_125_grades_query = SingleCourseStrmGradeQuery({'subject': 'CMPT', 'catalog_nbr': '125',
                                                            'emplids': passed_students_emplids})
        cmpt_125_grades_query_results = cmpt_125_grades_query.result()

        # Might as well get names in emails, to make it easier to double-check.
        email_query = EmailQuery()
        email = email_query.result()
        email.filter(EmailQuery.campus_email)

        name_query = NameQuery()
        names = name_query.result()

        cmpt_125_grades_query_results.left_join(names, "EMPLID")
        cmpt_125_grades_query_results.left_join(email, "EMPLID")

        # The final output
        self.artifacts.append(cmpt_125_grades_query_results)




