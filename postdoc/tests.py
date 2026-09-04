
import datetime
from django.test import TestCase
from courselib.testing import Client, freshen_roles, test_views
from postdoc.models import PostDoc, PostDocSupervisor, PostDocFundingSource
from coredata.models import Person, Unit, Role


class PostDocViewsTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_postdoc_pages(self):
        """
        Test basic page rendering
        """
        freshen_roles()
        c = Client()
        c.login_user('dzhao')

        # ensure user has PDMA role for admin actions
        admin = Person.objects.get(userid='dzhao')
        unit = Unit.objects.get(slug='cmpt')
        Role.objects.create(person=admin, role='PDMA', unit=unit, expiry=(datetime.date.today() + datetime.timedelta(days=30)))

        # basic pages
        test_views(self, c, 'postdoc:', ['post_doctoral_fellow', 'new_postdoc_appointment', 'download_index'], {})

        # create a PostDoc appointment to test view/edit pages
        p = Person.objects.exclude(userid='dzhao').first()
        appt = PostDoc.objects.create(person=p, unit=unit, type='INTERNAL', doctorate_completed_date=datetime.date.today(), work_eligibility_status='CANADIAN_CITIZEN', relocation_reimbursement=False,
                                      involved_teaching=False, start_date=datetime.date.today(), end_date=(datetime.date.today() + datetime.timedelta(days=30)), benefits_estimation=0,
                                      work_hours='FULL_TIME', hours_of_work=35, vacation_entitlement_weeks=5)

        # add a supervisor
        sup = Person.objects.get(userid='ggbaker')
        PostDocSupervisor.objects.create(postdoc=appt, supervisor=sup)

        # add a few funding sources
        PostDocFundingSource.objects.create(postdoc=appt, unit=2110, fund=11, project='123ABC', amount=500.00, start_date=appt.start_date, end_date=appt.end_date)
        PostDocFundingSource.objects.create(postdoc=appt, unit=2130, fund=13, project='ABC123', amount=500.00, start_date=appt.start_date, end_date=appt.end_date)

        test_views(self, c, 'postdoc:', ['view_postdoc_appointment', 'edit_postdoc_appointment'], {'postdoc_slug': appt.slug})
        test_views(self, c, 'postdoc:', ['appointee_appointments', 'supervisor_appointments'], {'userid': p.userid})
        test_views(self, c, 'postdoc:', ['edit_postdoc_notes', 'new_admin_attachment'], {'postdoc_slug': appt.slug})


