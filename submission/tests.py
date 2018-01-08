#from django.test import TestCase
from django.test import TestCase

from submission.models import URL, Archive, Code, StudentSubmission, select_all_components, ALL_TYPE_CLASSES
from submission.models.code import SubmittedCode
from submission.forms import filetype
from grades.models import NumericActivity, Activity
from groups.models import Group, GroupMember
from coredata.tests import create_offering, validate_content
from coredata.models import Member, Person, CourseOffering
from django.core.urlresolvers import reverse
from courselib.testing import Client, test_views, basic_page_tests, TEST_COURSE_SLUG
import datetime, tempfile, os

import base64, io
TGZ_FILE = base64.b64decode('H4sIAI7Wr0sAA+3OuxHCMBAE0CtFJUjoVw8BODfQP3bgGSKIcPResjO3G9w9/i9vRmt7ltnzZx6ilNrr7PVS9vscbUTKJ/wWr8fzuqYUy3pbvu1+9QAAAAAAAAAAAHCiNyHUDpAAKAAA')
GZ_FILE = base64.b64decode('H4sICIjWr0sAA2YAAwAAAAAAAAAAAA==')
ZIP_FILE = base64.b64decode('UEsDBAoAAAAAAMB6fDwAAAAAAAAAAAAAAAABABwAZlVUCQADiNavSzTYr0t1eAsAAQToAwAABOgDAABQSwECHgMKAAAAAADAenw8AAAAAAAAAAAAAAAAAQAYAAAAAAAAAAAApIEAAAAAZlVUBQADiNavS3V4CwABBOgDAAAE6AMAAFBLBQYAAAAAAQABAEcAAAA7AAAAAAA=')
RAR_FILE = base64.b64decode('UmFyIRoHAM+QcwAADQAAAAAAAABMpHQggCEACAAAAAAAAAADAAAAAMB6fDwdMwEApIEAAGYAv4hn9qn/1MQ9ewBABwA=')
PDF_FILE = base64.b64decode("""JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PC9MZW5ndGggNiAwIFIvRmlsdGVyIC9GbGF0ZURlY29k
ZT4+CnN0cmVhbQp4nCtUMNAzVDAAQSidnMulH2SukF7MZaDgDsTpXIVchmAFClAqOVfBKQSoyELB
yEAhJI0Los9QwdxIwdQAKJLLpeGRmpOTr1CeX5SToqgZksXlGsIVCIQA1l0XrmVuZHN0cmVhbQpl
bmRvYmoKNiAwIG9iago5MgplbmRvYmoKNCAwIG9iago8PC9UeXBlL1BhZ2UvTWVkaWFCb3ggWzAg
MCA2MTIgNzkyXQovUm90YXRlIDAvUGFyZW50IDMgMCBSCi9SZXNvdXJjZXM8PC9Qcm9jU2V0Wy9Q
REYgL1RleHRdCi9FeHRHU3RhdGUgOSAwIFIKL0ZvbnQgMTAgMCBSCj4+Ci9Db250ZW50cyA1IDAg
Ugo+PgplbmRvYmoKMyAwIG9iago8PCAvVHlwZSAvUGFnZXMgL0tpZHMgWwo0IDAgUgpdIC9Db3Vu
dCAxCj4+CmVuZG9iagoxIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cgL1BhZ2VzIDMgMCBSCi9NZXRh
ZGF0YSAxMSAwIFIKPj4KZW5kb2JqCjcgMCBvYmoKPDwvVHlwZS9FeHRHU3RhdGUKL09QTSAxPj5l
bmRvYmoKOSAwIG9iago8PC9SNwo3IDAgUj4+CmVuZG9iagoxMCAwIG9iago8PC9SOAo4IDAgUj4+
CmVuZG9iago4IDAgb2JqCjw8L0Jhc2VGb250L0NvdXJpZXIvVHlwZS9Gb250Ci9TdWJ0eXBlL1R5
cGUxPj4KZW5kb2JqCjExIDAgb2JqCjw8L1R5cGUvTWV0YWRhdGEKL1N1YnR5cGUvWE1ML0xlbmd0
aCAxMzE5Pj5zdHJlYW0KPD94cGFja2V0IGJlZ2luPSfvu78nIGlkPSdXNU0wTXBDZWhpSHpyZVN6
TlRjemtjOWQnPz4KPD9hZG9iZS14YXAtZmlsdGVycyBlc2M9IkNSTEYiPz4KPHg6eG1wbWV0YSB4
bWxuczp4PSdhZG9iZTpuczptZXRhLycgeDp4bXB0az0nWE1QIHRvb2xraXQgMi45LjEtMTMsIGZy
YW1ld29yayAxLjYnPgo8cmRmOlJERiB4bWxuczpyZGY9J2h0dHA6Ly93d3cudzMub3JnLzE5OTkv
MDIvMjItcmRmLXN5bnRheC1ucyMnIHhtbG5zOmlYPSdodHRwOi8vbnMuYWRvYmUuY29tL2lYLzEu
MC8nPgo8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0nM2YzY2FmMmYtNzJkNy0xMWVhLTAwMDAt
NmVhZWMyYzJlNmZkJyB4bWxuczpwZGY9J2h0dHA6Ly9ucy5hZG9iZS5jb20vcGRmLzEuMy8nIHBk
ZjpQcm9kdWNlcj0nR1BMIEdob3N0c2NyaXB0IDguNzAnLz4KPHJkZjpEZXNjcmlwdGlvbiByZGY6
YWJvdXQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcgeG1sbnM6eG1wPSdo
dHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvJz48eG1wOk1vZGlmeURhdGU+MjAxMC0wMy0yOFQx
NTozODo1OC0wNzowMDwveG1wOk1vZGlmeURhdGU+Cjx4bXA6Q3JlYXRlRGF0ZT4yMDEwLTAzLTI4
VDE1OjM4OjU4LTA3OjAwPC94bXA6Q3JlYXRlRGF0ZT4KPHhtcDpDcmVhdG9yVG9vbD5Vbmtub3du
QXBwbGljYXRpb248L3htcDpDcmVhdG9yVG9vbD48L3JkZjpEZXNjcmlwdGlvbj4KPHJkZjpEZXNj
cmlwdGlvbiByZGY6YWJvdXQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcg
eG1sbnM6eGFwTU09J2h0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8nIHhhcE1NOkRvY3Vt
ZW50SUQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcvPgo8cmRmOkRlc2Ny
aXB0aW9uIHJkZjphYm91dD0nM2YzY2FmMmYtNzJkNy0xMWVhLTAwMDAtNmVhZWMyYzJlNmZkJyB4
bWxuczpkYz0naHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8nIGRjOmZvcm1hdD0nYXBw
bGljYXRpb24vcGRmJz48ZGM6dGl0bGU+PHJkZjpBbHQ+PHJkZjpsaSB4bWw6bGFuZz0neC1kZWZh
dWx0Jz5VbnRpdGxlZDwvcmRmOmxpPjwvcmRmOkFsdD48L2RjOnRpdGxlPjwvcmRmOkRlc2NyaXB0
aW9uPgo8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgCjw/eHBhY2tldCBlbmQ9J3cnPz4KZW5kc3RyZWFtCmVuZG9iagoyIDAgb2JqCjw8L1Byb2R1
Y2VyKEdQTCBHaG9zdHNjcmlwdCA4LjcwKQovQ3JlYXRpb25EYXRlKEQ6MjAxMDAzMjgxNTM4NTgt
MDcnMDAnKQovTW9kRGF0ZShEOjIwMTAwMzI4MTUzODU4LTA3JzAwJyk+PmVuZG9iagp4cmVmCjAg
MTIKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwNDEzIDAwMDAwIG4gCjAwMDAwMDIwMzYgMDAw
MDAgbiAKMDAwMDAwMDM1NCAwMDAwMCBuIAowMDAwMDAwMTk1IDAwMDAwIG4gCjAwMDAwMDAwMTUg
MDAwMDAgbiAKMDAwMDAwMDE3NyAwMDAwMCBuIAowMDAwMDAwNDc4IDAwMDAwIG4gCjAwMDAwMDA1
NzggMDAwMDAgbiAKMDAwMDAwMDUxOSAwMDAwMCBuIAowMDAwMDAwNTQ4IDAwMDAwIG4gCjAwMDAw
MDA2NDAgMDAwMDAgbiAKdHJhaWxlcgo8PCAvU2l6ZSAxMiAvUm9vdCAxIDAgUiAvSW5mbyAyIDAg
UgovSUQgWzxFODIxMEZDNzI4OUJDM0Y5QzdCNEQxMjJDRjNCM0YwMD48RTgyMTBGQzcyODlCQzNG
OUM3QjREMTIyQ0YzQjNGMDA+XQo+PgpzdGFydHhyZWYKMjE1OQolJUVPRgo=""")



class SubmissionTest(TestCase):
    fixtures = ['basedata', 'coredata', 'grades']
    
    def setUp(self):
        pass

    def test_select_components(self):
        """
        Test submission component classes: subclasses, selection, sorting.
        """
        _, course = create_offering()
        a1 = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=course, position=2, max_grade=15, due_date="2010-04-01")
        a1.save()
        a2 = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=course, position=1, max_grade=15, due_date="2010-03-01")
        a2.save()

        p = Person.objects.get(userid="ggbaker")
        member = Member(person=p, offering=course, role="INST", career="NONS", added_reason="UNK")
        member.save()

        c1 = URL.Component(activity=a1, title="URL Link", position=8)
        c1.save()
        c2 = Archive.Component(activity=a1, title="Archive File", position=1, max_size=100000)
        c2.save()
        c3 = Code.Component(activity=a1, title="Code File", position=3, max_size=2000, allowed=".py")
        c3.save()
        comps = select_all_components(a1)
        self.assertEqual(len(comps), 3)
        self.assertEqual(comps[0].title, 'Archive File') # make sure position=1 is first
        self.assertEqual(str(comps[1].Type), "submission.models.code.Code")
        self.assertEqual(str(comps[2].Type), "submission.models.url.URL")

    def test_component_view_page(self):
        _, course = create_offering()
        a1 = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=course, position=2, max_grade=15, due_date="2010-04-01")
        a1.save()
        a2 = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=course, position=1, max_grade=15, due_date="2010-03-01")
        a2.save()

        p = Person.objects.get(userid="ggbaker")
        member = Member(person=p, offering=course, role="INST", career="NONS", added_reason="UNK")
        member.save()

        c1 = URL.Component(activity=a1, title="URL Link", position=8)
        c1.save()
        c2 = Archive.Component(activity=a1, title="Archive File", position=1, max_size=100000)
        c2.save()
        c3 = Code.Component(activity=a1, title="Code File", position=3, max_size=2000, allowed=".py")
        c3.save()
        client = Client()
        client.login_user("ggbaker")
        
        # When no component, should display error message
        url = reverse('offering:submission:show_components', kwargs={'course_slug':course.slug, 'activity_slug':a2.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, 'No components configured.')
        # add component and test
        component = URL.Component(activity=a2, title="URL2", position=1)
        component.save()
        component = Archive.Component(activity=a2, title="Archive2", position=1, max_size=100)
        component.save()
        # should all appear
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "URL2")
        self.assertContains(response, "Archive2")
        # make sure type displays
        #self.assertContains(response, '<li class="view"><label>Type:</label>Archive</li>')
        # delete component
        self.assertRaises(NotImplementedError, component.delete)

    def test_magic(self):
        """
        Test file type inference function
        """
        fh = io.StringIO(TGZ_FILE)
        fh.name = "something.tar.gz"
        ftype = filetype(fh)
        self.assertEqual(ftype, "TGZ")
        
        fh = io.StringIO(GZ_FILE)
        fh.name = "something.gz"
        ftype = filetype(fh)
        self.assertEqual(ftype, "GZIP")
        
        fh = io.StringIO(ZIP_FILE)
        fh.name = "something.zip"
        ftype = filetype(fh)
        self.assertEqual(ftype, "ZIP")
        
        fh = io.StringIO(RAR_FILE)
        fh.name = "something.rar"
        ftype = filetype(fh)
        self.assertEqual(ftype, "RAR")
        
        fh = io.StringIO(PDF_FILE)
        fh.name = "something.pdf"
        ftype = filetype(fh)
        self.assertEqual(ftype, "PDF")

        testfiles = [
                ('text.odt', 'OD-TEXT'),
                ('pres.odp', 'OD-PRES'),
                ('ss.ods', 'OD-SS'),
                ('drawing.odg', 'OD-GRA'),
                ('excel.xls', 'MS-EXCEL'),
                ('excel.xlsx', 'MS-EXCEL'),
                ('project.mpp', 'MS-PROJ'),
                ('visio.vsd', 'MS-VISIO'),
                ('word.doc', 'MS-WORD'),
                ('word.docx', 'MS-WORD'),
                ('pres.ppt', 'MS-PPT'),
                ('pres.pptx', 'MS-PPT'),
                ]
        
        for fn, ftype in testfiles:
            fh = open(os.path.join("submission", "testfiles", fn))
            ftypem = filetype(fh)
            self.assertEqual(ftype, ftypem)

    def test_group_submission_view(self):
        """
        test if group submission can be viewed by group member and non group member
        """
        now = datetime.datetime.now()
        _, course = create_offering()
        a1 = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=course, position=2, max_grade=15, due_date=now, group=True)
        a1.save()
        a2 = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=course, position=1, max_grade=15, due_date=now, group=True)
        a2.save()
        p = Person.objects.get(userid="ggbaker")
        member = Member(person=p, offering=course, role="INST", career="NONS", added_reason="UNK")
        member.save()
        c1 = URL.Component(activity=a1, title="URL Link", position=8)
        c1.save()
        c2 = Archive.Component(activity=a1, title="Archive File", position=1, max_size=100000)
        c2.save()
        c3 = Code.Component(activity=a1, title="Code File", position=3, max_size=2000, allowed=".py")
        c3.save()

        userid1 = "0aaa0"
        userid2 = "0aaa1"
        userid3 = "0aaa2"
        for u in [userid1, userid2,userid3]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=course, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        m = Member.objects.get(person__userid=userid1, offering=course)
        g = Group(name="Test Group", manager=m, courseoffering=course)
        g.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()
        m = Member.objects.get(person__userid=userid2, offering=course)
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a1)
        gm.save()
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()
        m = Member.objects.get(person__userid=userid3, offering=course)
        gm = GroupMember(group=g, student=m, confirmed=True, activity=a2)
        gm.save()

        client = Client()
        # login as "0aaa0", member of group : test_group for assignment1 and assgnment2
        client.login_user("0aaa0")

        #submission page for assignment 1
        url = reverse('offering:submission:show_components', kwargs={'course_slug': course.slug,'activity_slug':a1.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "This is a group activity. You will submit on behalf of the group &ldquo;Test Group&rdquo;.")
        self.assertContains(response, "You haven't made a submission for this component.")


    def test_upload(self):
        _, course = create_offering()
        a1 = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=course, position=2, max_grade=15, due_date=datetime.datetime.now() + datetime.timedelta(hours=1), group=False)
        a1.save()
        p = Person.objects.get(userid="ggbaker")
        member = Member(person=p, offering=course, role="INST", career="NONS", added_reason="UNK")
        member.save()
        c = Code.Component(activity=a1, title="Code File", position=3, max_size=2000, allowed=".py")
        c.save()

        userid1 = "0aaa0"
        userid2 = "0aaa1"
        userid3 = "0aaa2"
        for u in [userid1, userid2,userid3]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=course, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        
        # submit as student
        client = Client()
        client.login_user("0aaa0")
        url = reverse('offering:submission:show_components', kwargs={'course_slug': course.slug,'activity_slug':a1.slug})
        response = basic_page_tests(self, client, url)

        # submit a file
        tmpf = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        codecontents = 'print "Hello World!"\n'
        tmpf.write(codecontents)
        tmpf.close()

        try:
            fh = open(tmpf.name, "r")
            data = {"%i-code" % (c.id): fh}
            response = client.post(url, data)
            self.assertEqual(response.status_code, 302)
            
        finally:
            os.unlink(tmpf.name)

        # make sure it's there and correct
        subs = StudentSubmission.objects.all()
        self.assertEqual(len(subs), 1)
        sub = subs[0]
        self.assertEqual(sub.member.person.userid, '0aaa0')
            
        codes = SubmittedCode.objects.all()
        self.assertEqual(len(codes), 1)
        code = codes[0]
        code.code.open()
        self.assertEqual(code.code.read(), codecontents)
            
    def test_pages(self):
        "Test a bunch of page views"
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        activity = Activity.objects.get(offering=offering, slug='rep')
        activity.due_date = datetime.datetime.now() + datetime.timedelta(days=1) # make sure it's submittable
        activity.save()
        client = Client()

        # instructor views
        client.login_user("ggbaker")

        component1 = URL.Component(activity=activity, title='Sample URL 1', description='Please submit some URL.',
                                   check=False, prefix='')
        component1.save()
        component2 = URL.Component(activity=activity, title='Sample URL 2', description='Please submit some URL.',
                                   check=False, prefix='')
        component2.save()

        test_views(self, client, 'offering:submission:', ['show_components', 'add_component'],
                   {'course_slug': offering.slug, 'activity_slug': activity.slug})

        url = reverse('offering:submission:edit_single', kwargs={'course_slug': offering.slug, 'activity_slug': activity.slug}) \
                + '?id=' + str(component1.id)
        basic_page_tests(self, client, url)

        url = reverse('offering:submission:add_component', kwargs={'course_slug': offering.slug, 'activity_slug': activity.slug}) \
                + '?type=url'
        basic_page_tests(self, client, url)

        # student views: with none, some, and all submitted
        client.login_user("0aaa0")

        # test various permutations of success to make sure everything returns okay
        name1 = '%i-url' % (component1.id)
        name2 = '%i-url' % (component2.id)
        submissions = [
            ({}, False),
            ({name1: '', name2: ''}, False),
            ({name1: '', name2: 'do i look like a url to you?'}, False),
            ({name1: 'http://www.sfu.ca/', name2: ''}, False),
            ({name1: 'http://www.cs.sfu.ca/', name2: 'http://example.com/'}, True),
            ({name1: 'http://www.sfu.ca/', name2: 'http://example.com/'}, True),
        ]
        for submitdata, redir in submissions:
            test_views(self, client, 'offering:submission:', ['show_components', 'show_components_submission_history'],
                       {'course_slug': offering.slug, 'activity_slug': activity.slug})
            url = reverse('offering:submission:show_components', kwargs={'course_slug': offering.slug, 'activity_slug': activity.slug})
            response = client.post(url, submitdata)
            if redir:
                # success: we expect a redirect
                self.assertEqual(response.status_code, 302)
            else:
                # some problems: expect a page reporting that
                self.assertEqual(response.status_code, 200)
                validate_content(self, response.content, url)

    def test_submission_types(self):
        "Minimally test each submission type"
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        activity = Activity.objects.get(offering=offering, slug='rep')
        activity.due_date = datetime.datetime.now() + datetime.timedelta(days=1) # make sure it's submittable
        activity.save()
        client = Client()

        # instructor views
        client.login_user("ggbaker")

        for Type in ALL_TYPE_CLASSES:
            label = Type.label
            test_views(self, client, 'offering:submission:', ['add_component'],
                   {'course_slug': offering.slug, 'activity_slug': activity.slug}, qs='type='+label)









