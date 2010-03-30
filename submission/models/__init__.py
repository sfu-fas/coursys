from django.db import models
#from grades.models import Activity
#from coredata.models import Member, Person,CourseOffering
#from courses.grades.models import slug
from groups.models import Group,GroupMember
from datetime import datetime
from autoslug import AutoSlugField

from django.shortcuts import get_object_or_404
from django.core.servers.basehttp import FileWrapper
import zipfile
import tempfile
import os, gzip
from django.http import HttpResponse

from base import SubmissionComponent, Submission, StudentSubmission, GroupSubmission, SubmittedComponent

from url import *
from archive import *
from pdf import *
ALL_TYPE_CLASSES = [Archive, URL, PDF]

def find_type_by_label(label):
    """
    Find the submission component class based on the label.  Returns None if not found.
    """
    for Type in ALL_TYPE_CLASSES:
        if Type.label == label:
            return Type
    return None



"""
All the subclasses follow the convention that
its name is xxxComponent where xxx will be used as type identification
"""
#class URLComponent(SubmissionComponent):
#    "A URL submission component"
#class ArchiveComponent(SubmissionComponent):
#    "An archive file (TGZ/ZIP/RAR) submission component"
#    max_size = models.PositiveIntegerField(help_text="Maximum size of the archive file, in KB.", null=True, default=10000)
#    extension = [".zip", ".rar", ".gzip", ".tar"]
#class CppComponent(SubmissionComponent):
#    "C/C++ file submission component"
#    extension = [".c", ".cpp", ".cxx"]
#class PlainTextComponent(SubmissionComponent):
#    "Text file submission component"
#    max_length = models.PositiveIntegerField(help_text="Maximum number of characters for plain text.", null=True, default=5000)
#class JavaComponent(SubmissionComponent):
#    "Java file submission component"
#    extension = [".java"]

# list of all subclasses of SubmissionComponent:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
#COMPONENT_TYPES = [URLComponent, ArchiveComponent, CppComponent, PlainTextComponent, JavaComponent]

def select_all_components(activity):
    """
    Return all components for this activity as their most specific class.
    """
    components = [] # list of components
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for Type in ALL_TYPE_CLASSES:
        comps = list(Type.Component.objects.filter(activity=activity))
        components.extend( (c for c in comps if c.id not in found) )
        found.update( (c.id for c in comps) )

    components.sort()
    return components




#class SubmittedURL(SubmittedComponent):
#    component = models.ForeignKey(URL.SubmissionComponent, null=False)
#    url = models.URLField(verify_exists=True,blank = True)
#    def get_url(self):
#        return self.url
#    def get_size(self):
#        return None
#class SubmittedArchive(SubmittedComponent):
#    component = models.ForeignKey(ArchiveComponent, null=False)
#    archive = models.FileField(upload_to="submittedarchive", blank = True) # TODO: change to a more secure directory
#    def get_url(self):
#        return self.archive.url
#    def get_size(self):
#        return self.archive.size

#class SubmittedCpp(SubmittedComponent):
#    component = models.ForeignKey(CppComponent, null=False)
#    cpp = models.FileField(upload_to="submittedcpp", blank = True) # TODO: change to a more secure directory
#    def get_url(self):
#        return self.cpp.url
#    def get_size(self):
#        return self.cpp.size

#class SubmittedPlainText(SubmittedComponent):
#    component = models.ForeignKey(PlainTextComponent, null=False)
#    text = models.TextField(max_length=3000)
#    def get_url(self):
#        return self.text.url
#    def get_size(self):
#        return self.text.size

#class SubmittedJava(SubmittedComponent):
#    component = models.ForeignKey(JavaComponent, null=False)
#    java = models.FileField(upload_to="submittedjava", blank = True) # TODO: change to a more secure directory
#    def get_url(self):
#        return self.java.url
#    def get_size(self):
#        return self.java.size


#SUBMITTED_TYPES = [SubmittedURL, SubmittedArchive, SubmittedCpp, SubmittedPlainText, SubmittedJava]
def select_all_submitted_components(activity):
    submitted_component = [] # list of submitted component
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for Type in ALL_TYPE_CLASSES:
        subs = list(Type.SubmittedComponent.objects.filter(submission__activity = activity))
        submitted_component.extend(s for s in subs if s.id not in found)
        found.update( (s.id for s in subs) )
    submitted_component.sort()
    return submitted_component

# TODO: group submission selector
def XXX_select_students_submitted_components(activity, userid):
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

def XXX_select_students_submission_by_component(component, userid):
    submitted_component = select_students_submitted_components(component.activity ,userid)
    new_submitted_component = [comp for comp in submitted_component if comp.component == component]
    new_submitted_component.sort()
    return new_submitted_component



def get_component(**kwargs):
    """
    Find the submission component (with the most specific type).  Returns None if doesn't exist.
    """
    for Type in ALL_TYPE_CLASSES:
        res = Type.Component.objects.filter(**kwargs)
        res = list(res)
        if len(res) > 1:
            raise ValueError, "Search returned multiple values."
        elif len(res) == 1:
            return res[0]

    return None
        
def get_submitted_component(**kwargs):
    """
    Find the submitted component (with the most specific type).  Returns None if doesn't exist.
    """
    for Type in ALL_TYPE_CLASSES:
        res = Type.SubmittedComponent.objects.filter(**kwargs)
        res = list(res)
        if len(res) > 1:
            raise ValueError, "Search returned multiple values."
        elif len(res) == 1:
            return res[0]

    return None
        
        

#def check_component_id_type_activity(list, id, type, activity):
#    """
#    check if id/type/activity matches for some component in the list.
#    if they match, return that component
#    """
#    if id == None or type == None:
#        return None
#    for c in list:
#        if str(c.get_type()) == type and str(c.id) == id and c.activity == activity:
#            return c
#    return None

def get_submission_components(submission, activity, component_list=None):
    """
    return a list of pair[component, latest_submission(could be None)] for this submission
    """
    if not component_list:
        component_list = select_all_components(activity)
    
    submitted_components = []
    for component in component_list:
        if submission:
            SubmittedComponent = component.Type.SubmittedComponent
            submits = SubmittedComponent.objects.filter(component=component, submission=submission)
            if submits:
                sub = submits[0]
            else:
                # this component didn't get submitted
                sub = None
        else:
            sub = None

        submitted_components.append((component, sub))

    return submitted_components

def get_current_submission(student, activity):
    """
    find most recent submission (individual or group)
    """
    if activity.group:
        gms = GroupMember.objects.filter(student__person=student, confirmed=True)
        try:
            submission = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms).latest('created_at')
        except GroupSubmission.DoesNotExist:
            submission = None
    else:
        try:
            submission = StudentSubmission.objects.filter(activity=activity, member__person=student).latest('created_at')
        except StudentSubmission.DoesNotExist:
            submission = None

    if submission:
        submitted_components = get_submission_components(submission, activity)
    else:
        submitted_components = get_submission_components(None, activity)

    return submission, submitted_components

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

def generate_zip_file(submission, submitted_components):
    """
    return a zip file containing latest submission from userid for activity
    """
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w', zipfile.ZIP_STORED)

    for component, sub in submitted_components:
        if sub:
            sub.add_to_zip(z)

    z.close()

    file = open(filename, 'rb')
    response = HttpResponse(FileWrapper(file), mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s'% submission.file_slug() + "_" + submission.activity.slug + ".zip"
    try:
        os.remove(filename)
    except OSError:
        print "Warning: error removing temporary file."
    return response

