from django.db import models
from grades.models import Activity
from coredata.models import Member, Person,CourseOffering
#from courses.grades.models import slug
from groups.models import Group,GroupMember
from datetime import datetime
from autoslug import AutoSlugField
from django.shortcuts import get_object_or_404
from django.core.servers.basehttp import FileWrapper
import zipfile
import tempfile
import os
from django.http import HttpResponse
from dashboard.models import NewsItem
from django.core.urlresolvers import reverse
from django.db.models import Max

STATUS_CHOICES = [
    ('NEW', 'New'),
    ('INP', 'In-Progress'),
    ('DON', 'Marked') ]

TYPE_CHOICES = [
    ('Archive', 'Archive Component'),
    ('URL', 'URL Component'),
    ('Cpp', 'C/C++ Component'),
    ('PlainText', 'Plain Text Component'),
    ('Java', 'Java Component'),
]

# per-activity models, defined by instructor:

class SubmissionComponent(models.Model):
    """
    A component of the activity that will be submitted by students
    """
    activity = models.ForeignKey(Activity)
    title = models.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    description = models.CharField(max_length=1000, help_text="Short explanation for this component.", null=True,blank=True)
    position = models.PositiveSmallIntegerField(help_text="The order of display for listing components.", null=True,blank=True)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with='activity')

    def __cmp__(self, other):
        return cmp(self.position, other.position)
    class Meta:
        ordering = ['position']
    def __unicode__(self):
        return "%s[%s]%s"%(self.title, self.get_type(), self.description)
    def get_type(self):
        "Return xxx of xxxComponent as type"
        class_name = self.__class__.__name__
        return class_name[:class_name.index("Component")]
        
    def save(self):
        if self.position == None:
            lastpos = SubmissionComponent.objects.filter(activity=self.activity) \
                    .aggregate(Max('position'))['position__max']
            if lastpos is None:
                lastpos = 0
            self.position = lastpos+1
        super(SubmissionComponent, self).save()

"""
All the subclasses follow the convention that
its name is xxxComponent where xxx will be used as type identification
"""
class URLComponent(SubmissionComponent):
    "A URL submission component"
class ArchiveComponent(SubmissionComponent):
    "An archive file (TGZ/ZIP/RAR) submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the archive file, in KB.", null=True, default=10000)
    extension = [".zip", ".rar", ".gzip", ".tar"]
class CppComponent(SubmissionComponent):
    "C/C++ file submission component"
    extension = [".c", ".cpp", ".cxx"]
class PlainTextComponent(SubmissionComponent):
    "Text file submission component"
    max_length = models.PositiveIntegerField(help_text="Maximum number of characters for plain text.", null=True, default=5000)
class JavaComponent(SubmissionComponent):
    "Java file submission component"
    extension = [".java"]

# list of all subclasses of SubmissionComponent:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
COMPONENT_TYPES = [URLComponent, ArchiveComponent, CppComponent, PlainTextComponent, JavaComponent]

def select_all_components(activity):
    """
    Return all components for this activity as their most specific class.
    """
    components = [] # list of components
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for ComponentType in COMPONENT_TYPES:
        comps = list(ComponentType.objects.filter(activity=activity))
        components.extend( (c for c in comps if c.id not in found) )
        found.update( (c.id for c in comps) )

    components.sort()
    count = 1;
    for component in components:
        component.position = count
        count = count + 1
        component.save()
    return components



# per-submission models, created when a student/group submits an assignment:

class Submission(models.Model):
    """
    A student's or group's submission for an activity
    """
    activity = models.ForeignKey(Activity)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Member, null=True, help_text = "TA or instructor that will mark this submission")
    status = models.CharField(max_length=3, null=False,choices=STATUS_CHOICES, default = "NEW")

    "Set ownership, and make state = in progree "
    def set_owner(self, course, userid):
        member = Member.objects.filter(person__userid = userid).filter(offering = course)
        if member != []:
            self.owner = member[0]
            self.status = "INP"
            self.save()
    def get_type(self):
        g = GroupSubmission.objects.filter(pk = self.pk)
        if len(g) > 0:
            return "Group"
        return "student"
    def get_derived_class(self):
        if self.get_type() == "Group":
            return GroupSubmission.objects.all().get(pk = self.pk)
        else:
            return StudentSubmission.objects.all().get(pk = self.pk)
    def get_userid(self):
        return self.get_derived_class().get_userid()

class StudentSubmission(Submission):
    member = models.ForeignKey(Member, null=False)
    def get_userid(self):
        return self.member.person.userid
    def __unicode__(self):
        return "%s->%s@%s" % (self.member.person.userid, self.activity, self.created_at)

class GroupSubmission(Submission):
    group = models.ForeignKey(Group, null=False)
    creator = models.ForeignKey(GroupMember, null = False)

    #TODO: add a item indicate who submit the assignment

    def get_userid(self):
        return self.group.slug[2:]
    def __unicode__(self):
        return "%s->%s@%s" % (self.creator.student.person.userid, self.activity, self.created_at)

    def save(self):
        super(GroupSubmission, self).save()
        member_list = GroupMember.objects.exclude(student = self.creator).filter(group = self.group)
        for member in member_list:
            n = NewsItem(user = member.student.person, author=self.creator.student.person, course=member.group.courseoffering,
                source_app="group submission", title="New Group Submission",
                content="Your group member %s has new submission for %s."
                    % (self.creator.student.person,self.activity),
                url=reverse('submission.views.show_components', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': member.activity.slug})
                )
            n.save()


# parts of a submission, created as part of a student/group submission

class SubmittedComponent(models.Model):
    """
    Part of a student's/group's submission
    """
    submission = models.ForeignKey(Submission)
    submit_time = models.DateTimeField(auto_now_add = True)
    def get_time(self):
        "return the submit time of the component"
        return self.submit_time.strftime("%Y-%m-%d %H:%M:%S")
    def get_late_time(self):
        "return how late the submission is"
        time = self.submission.create_at - self.activity.due_date
        if time < datetime.datedelta():
            return 0
        else:
            return time
    def __cmp__(self, other):
        return cmp(other.submit_time, self.submit_time)
    class Meta:
        ordering = ['submit_time']
    def get_type(self):
        "Return xxx of Submittedxxx as type"
        class_name = self.__class__.__name__
        return class_name[9:]
    def get_size_in_kb(self):
        res = int(self.get_size())/1024
        return res
    def __unicode__(self):
        return "[%s] %s->%s@%s" % (self.get_type(), self.submission.get_userid(), self.submission.activity, self.submission.created_at)



class SubmittedURL(SubmittedComponent):
    component = models.ForeignKey(URLComponent, null=False)
    url = models.URLField(verify_exists=True,blank = True)
    def get_url(self):
        return self.url
    def get_size(self):
        return None
class SubmittedArchive(SubmittedComponent):
    component = models.ForeignKey(ArchiveComponent, null=False)
    archive = models.FileField(upload_to="submission/submittedarchive", blank = True) # TODO: change to a more secure directory
    def get_url(self):
        return self.archive.url
    def get_size(self):
        return self.archive.size

class SubmittedCpp(SubmittedComponent):
    component = models.ForeignKey(CppComponent, null=False)
    cpp = models.FileField(upload_to="submission/submittedcpp", blank = True) # TODO: change to a more secure directory
    def get_url(self):
        return self.cpp.url
    def get_size(self):
        return self.cpp.size

class SubmittedPlainText(SubmittedComponent):
    component = models.ForeignKey(PlainTextComponent, null=False)
    text = models.TextField(max_length=3000)
    def get_url(self):
        return self.text.url
    def get_size(self):
        return self.text.size

class SubmittedJava(SubmittedComponent):
    component = models.ForeignKey(JavaComponent, null=False)
    java = models.FileField(upload_to="submission/submittedjava", blank = True) # TODO: change to a more secure directory
    def get_url(self):
        return self.java.url
    def get_size(self):
        return self.java.size


SUBMITTED_TYPES = [SubmittedURL, SubmittedArchive, SubmittedCpp, SubmittedPlainText, SubmittedJava]
def select_all_submitted_components(activity):
    submitted_component = [] # list of submitted component
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for SubmittedType in SUBMITTED_TYPES:
        subs = list(SubmittedType.objects.filter(submission__activity = activity))
        submitted_component.extend(s for s in subs if s.id not in found)
        found.update( (s.id for s in subs) )
    submitted_component.sort()
    return submitted_component

# TODO: group submission selector
def select_students_submitted_components(activity, userid):
    submitted_component = select_all_submitted_components(activity)
    new_submitted_component = []
    for comp in submitted_component:
        if comp.submission.get_type() == 'Group':
            group_submission = GroupSubmission.objects.all().get(pk = comp.submission.pk)
            member = GroupMember.objects.all().filter(group = group_submission.group)\
            .filter(student__person__userid=userid)\
            .filter(activity = activity)\
            .filter(confirmed = True)
            if len(member)>0:
                new_submitted_component.append(comp)
        else:
            student_submission = StudentSubmission.objects.all().get(pk = comp.submission.pk)
            if student_submission.member.person.userid == userid:
                new_submitted_component.append(comp)
    new_submitted_component.sort()
    return new_submitted_component

def select_students_submission_by_component(component, userid):
    submitted_component = select_students_submitted_components(component.activity ,userid)
    new_submitted_component = [comp for comp in submitted_component if comp.component == component]
    new_submitted_component.sort()
    return new_submitted_component

def filetype(file):
  """
  Do some magic to guess the filetype.
  """
  # methods extracted from the magic file (/usr/share/file/magic)
  # why not just check the filename?  Students seem to randomly rename.
  file.seek(0)
  magic = file.read(4)
  if magic=="PK\003\004" or magic=="PK00":
      return ".ZIP"
  elif magic=="Rar!":
      return ".RAR"
  elif magic[0:2]=="\037\213":
      return ".GZIP"

  file.seek(257)
  if file.read(5)=="ustar":
      return ".TAR"

  return file.name[file.name.rfind('.'):]



def check_component_id_type_activity(list, id, type, activity):
    """
    check if id/type/activity matches for some component in the list.
    if they match, return that component
    """
    if id == None or type == None:
        return None
    for c in list:
        if str(c.get_type()) == type and str(c.id) == id and c.activity == activity:
            return c
    return None

def get_current_submission(userid, activity):
    """
    return a list of pair[component, latest_submission(could be None)]
    """
    component_list = select_all_components(activity)
    all_submitted = select_students_submitted_components(activity, userid)
    #TODO: group submission
    submitted_pair_list = []
    for component in component_list:
        pair = []
        pair.append(component)
        c = [sub for sub in all_submitted if sub.component == component]
        c.sort()
        if len(c) == 0:
            pair.append(None)
        else:
            pair.append(c[0])
        submitted_pair_list.append(pair)
    return submitted_pair_list

def get_submit_time_and_owner(activity, pair_list):
    """
    returns (late time, latest submit_time, ownership)
    """
    #calculate latest submission
    submit_time = None
    owner = None
    for pair in pair_list:
        if pair[1] != None:
            try:
                if submit_time == None:
                    submit_time = datetime.min
            except:
                pass
            if pair[1].submission.owner != None:
                owner = pair[1].submission.owner.person
            if submit_time < pair[1].submission.created_at:
                submit_time = pair[1].submission.created_at
    late = None
    if submit_time != None and submit_time > activity.due_date:
        late = submit_time - activity.due_date
    return late, submit_time, owner

def download_single_component(type, id):
    """
    identified by component.type and component.id
    """
    if type == 'PlainText':
        text_component = get_object_or_404(SubmittedPlainText, id = id)
        return _download_text_file(text_component)
    if type == 'URL':
        url_component = get_object_or_404(SubmittedURL, id=id)
        return _download_url_file(url_component)
    if type == 'Archive':
        archive_component = get_object_or_404(SubmittedArchive, id=id)
        return _download_archive_file(archive_component)
    if type == 'Cpp':
        cpp_component = get_object_or_404(SubmittedCpp, id=id)
        return _download_cpp_file(cpp_component)
    if type == 'Java':
        java_component = get_object_or_404(SubmittedJava, id=id)
        return _download_java_file(java_component)
    return NotFoundResponse(request)

def generate_zip_file(pair_list, userid, activity_slug):
    """
    return a zip file containing latest submission from userid for activity
    """
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w', zipfile.ZIP_STORED)

    for pair in pair_list:
        if pair[1] == None:
            continue
        type = pair[0].get_type()
        if type == 'PlainText':
            z.writestr(pair[0].slug+".txt", pair[1].text)
        if type == 'URL':
            content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL='
            if str(pair[1].url).find("://") == -1:
                content += "http://"
            content += pair[1].url
            content += '"></head><body>' \
                + 'If redirecting doesn\' work, click the link <a href="' \
                + pair[1].url + '">' + pair[1].url + '</a>' \
                + '</body></html> '
            z.writestr(pair[0].slug+".html", content)
        if type == 'Archive':
            name = pair[1].archive.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].archive.path, name)
        if type == 'Cpp':
            name = pair[1].cpp.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].cpp.path, name)
        if type == 'Java':
            name = pair[1].java.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].java.path, name)
    z.close()

    file = open(filename, 'rb')
    response = HttpResponse(FileWrapper(file), mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s'% userid + "_" + activity_slug + ".zip"
    try:
        os.remove(filename)
    except OSError:
        print "Warning: error removing temporary file."
    return response

def _download_text_file(submission):
    """
    return a txt file attachment
    """
    response = HttpResponse(submission.text, mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + ".txt"
    return response

def _download_url_file(submission):
    """
    return a .html file with redirect information
    """
    content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL='
    if str(submission.url).find("://") == -1:
        content += "http://"
    content += submission.url
    content += '"></head><body>' \
        + 'If redirecting doesn\' work, click the link <a href="' \
        + submission.url + '">' + submission.url + '</a>' \
        + '</body></html> '
    response = HttpResponse(content, mimetype='text/html')
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + ".html"
    return response

def _download_archive_file(submission):
    response = HttpResponse(submission.archive, mimetype='application/octet-stream')
    filename = submission.archive.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response

def _download_cpp_file(submission):
    response = HttpResponse(submission.cpp, mimetype='text/plain')
    filename = submission.cpp.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response

def _download_java_file(submission):
    response = HttpResponse(submission.java, mimetype='text/plain')
    filename = submission.java.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response
