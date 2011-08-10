from django.test import *
from django.test.client import Client
from submission.models import *
from submission.models.code import SubmittedCode
from submission.forms import *
from grades.models import NumericActivity
from coredata.tests import create_offering
from settings import CAS_SERVER_URL
from coredata.models import *
from courselib.testing import *
import gzip, tempfile, os

import base64, StringIO, zlib
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
ODT_FILE = zlib.decompress(base64.b64decode("""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
+ZlLeZteLi6fFVvWR+BpKxLP2p/LmDWY33ZJe
+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
+xEmBgD4Dt6B/wPwyWMe"""))



class SubmissionTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        pass

    def test_select_components(self):
        """
        Test submission component classes: subclasses, selection, sorting.
        """
        s, course = create_offering()
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
        self.assertEqual(str(comps[1].Type), "courses.submission.models.code.Code")
        self.assertEqual(str(comps[2].Type), "courses.submission.models.url.URL")

    def test_component_view_page(self):
        s, course = create_offering()
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
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        # When no component, should display error message
        url = reverse('submission.views.show_components', kwargs={'course_slug':course.slug, 'activity_slug':a2.slug})
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
        self.assertContains(response, '<li class="view"><label>Type:</label>Archive</li>')
        # delete component
        self.assertRaises(NotImplementedError, component.delete)

    def test_magic(self):
        """
        Test file type inference function
        """
        fh = StringIO.StringIO(TGZ_FILE)
        fh.name = "something.tar.gz"
        ftype = filetype(fh)
        self.assertEqual(ftype, "TGZ")
        
        fh = StringIO.StringIO(GZ_FILE)
        fh.name = "something.gz"
        ftype = filetype(fh)
        self.assertEqual(ftype, "GZIP")
        
        fh = StringIO.StringIO(ZIP_FILE)
        fh.name = "something.zip"
        ftype = filetype(fh)
        self.assertEqual(ftype, "ZIP")
        
        fh = StringIO.StringIO(RAR_FILE)
        fh.name = "something.rar"
        ftype = filetype(fh)
        self.assertEqual(ftype, "RAR")
        
        fh = StringIO.StringIO(PDF_FILE)
        fh.name = "something.pdf"
        ftype = filetype(fh)
        self.assertEqual(ftype, "PDF")

        fh = StringIO.StringIO(ODT_FILE)
        fh.name = "something.odt"
        ftype = filetype(fh)
        self.assertEqual(ftype, "OPENDOC")



    def test_group_submission_view(self):
        """
        test if group submission can be viewed by group member and non group member
        """
        now = datetime.datetime.now()
        s, course = create_offering()
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
        client.login(ticket = "0aaa0", service = CAS_SERVER_URL)

        #submission page for assignment 1
        url = reverse('submission.views.show_components', kwargs={'course_slug': course.slug,'activity_slug':a1.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "This is a group submission. You will submit on behalf of the group Test Group.")
        self.assertContains(response, "You haven't made a submission for this component.")


    def test_upload(self):
        s, course = create_offering()
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
        client.login(ticket="0aaa0", service=CAS_SERVER_URL)
        url = reverse('submission.views.show_components', kwargs={'course_slug': course.slug,'activity_slug':a1.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, '<input type="file" name="%i-code"' % (c.id))
        
        # submit a file
        tmpf = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        codecontents = 'print "Hello World!"\n'
        tmpf.write(codecontents)
        tmpf.close()

        try:
            fh = open(tmpf.name, "r")
            data = {"%i-code" % (c.id): fh}
            response = client.post(url, data)
            self.assertEquals(response.status_code, 302)
            
        finally:
            os.unlink(tmpf.name)

        # make sure it's there and correct
        subs = StudentSubmission.objects.all()
        self.assertEquals(len(subs), 1)
        sub = subs[0]
        self.assertEquals(sub.member.person.userid, '0aaa0')
            
        codes = SubmittedCode.objects.all()
        self.assertEquals(len(codes), 1)
        code = codes[0]
        code.code.open()
        self.assertEquals(code.code.read(), codecontents)
            



