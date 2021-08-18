from django.test import TestCase
from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG, Client, test_views
from discipline.models import DisciplineCaseInstrStudent, DisciplineGroup
from discipline.views import STEP_FORM

class DisciplineTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_pages(self):
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        student = Member.objects.get(offering=offering, person__userid='0aaa0')
        instr = Member.objects.get(offering=offering, person__userid='ggbaker')
        c = Client()
        c.login_user('ggbaker')

        test_views(self, c, 'offering:discipline:', ['index', 'new', 'newgroup', 'new_nonstudent'],
                   {'course_slug': offering.slug})

        cluster = DisciplineGroup(name='TheCluster', offering=offering)
        cluster.save()
        case = DisciplineCaseInstrStudent(student=student.person, owner=instr.person, offering=offering, group=cluster)
        case.save()

        test_views(self, c, 'offering:discipline:', ['showgroup'],
                   {'course_slug': offering.slug, 'group_slug': cluster.slug})
        test_views(self, c, 'offering:discipline:', ['show', 'edit_related', 'edit_attach', 'new_file'],
                   {'course_slug': offering.slug, 'case_slug': case.slug})

        # have a look at each form
        for step in STEP_FORM:
            test_views(self, c, 'offering:discipline:', ['edit_case_info'],
                       {'course_slug': offering.slug, 'case_slug': case.slug, 'field': step})

        # minimally-finish the case so we can check the letter
        case.letter_sent = 'MAIL'
        case.letter_text = 'foo'
        case.save()
        test_views(self, c, 'offering:discipline:', ['view_letter'],
                   {'course_slug': offering.slug, 'case_slug': case.slug})
