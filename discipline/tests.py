from django.test import TestCase
from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG, Client, test_views
from discipline.models import DisciplineCaseInstrStudent, DisciplineGroup
from django.urls import reverse


class DisciplineTest(TestCase):
    fixtures = ['basedata', 'coredata', 'discipline']

    def post_it(self, case, view, data, status_code=302):
        url = reverse('offering:discipline:' + view, kwargs={'course_slug': case.offering.slug, 'case_slug': case.slug})
        resp = self.client.post(url, data=data)
        self.assertEqual(resp.status_code, status_code)

    def test_pages(self):
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        student = Member.objects.get(offering=offering, person__userid='0aaa0')
        instr = Member.objects.get(offering=offering, person__userid='ggbaker')
        c = Client()
        self.client = c
        c.login_user('ggbaker')

        test_views(self, c, 'offering:discipline:', ['index', 'new', 'newgroup', 'new_nonstudent'],
                   {'course_slug': offering.slug})

        cluster = DisciplineGroup(name='TheCluster', offering=offering)
        cluster.save()
        case = DisciplineCaseInstrStudent(student=student.person, owner=instr.person, offering=offering, group=cluster)
        case.save()

        test_views(self, c, 'offering:discipline:', ['showgroup'],
                   {'course_slug': offering.slug, 'group_slug': cluster.slug})
        test_views(self, c, 'offering:discipline:', ['show', 'edit_attach', 'new_file'],
                   {'course_slug': offering.slug, 'case_slug': case.slug})

        # run through the case in views to make sure it evolves as we expect.
        self.post_it(case, 'notes', {'notes_0': 'I am suspicious. _Very_ suspicious', 'notes_1': 'textile'})
        self.post_it(case, 'notify', {'notify': 'OTHR'})
        self.post_it(case, 'response', {'response': 'MET'})
        self.post_it(case, 'facts', {'facts_0': 'It was a dishonesty.', 'facts_1': 'markdown'})
        self.post_it(case, 'penalty', {'penalty': 'ZERO', 'penalty_reason_0': 'It was a bad.', 'penalty_reason_1': 'markdown'})

        # have a look at each form
        test_views(self, c, 'offering:discipline:', ['notify', 'facts', 'penalty', 'send', 'notes', 'edit_attach'],
                   {'course_slug': offering.slug, 'case_slug': case.slug})

        # letter should not be visible yet: unsent
        letter_url = reverse('offering:discipline:view_letter', kwargs={'course_slug': offering.slug, 'case_slug': case.slug})
        resp = c.get(letter_url)
        self.assertEqual(resp.status_code, 403)

        self.post_it(case, 'send', {'letter_review': 'on'})

        # edits should fail now
        self.post_it(case, 'penalty', {'penalty': 'NONE', 'penalty_reason_0': 'It was worse.', 'penalty_reason_1': 'markdown'}, status_code=403)

        # but letter should now be visible
        test_views(self, c, 'offering:discipline:', ['view_letter'], {'course_slug': offering.slug, 'case_slug': case.slug})
