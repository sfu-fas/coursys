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
from code import *
ALL_TYPE_CLASSES = [Archive, URL, PDF, Code]

def find_type_by_label(label):
    """
    Find the submission component class based on the label.  Returns None if not found.
    """
    for Type in ALL_TYPE_CLASSES:
        if Type.label == label:
            return Type
    return None


def select_all_components(activity, include_deleted=False):
    """
    Return all components for this activity as their most specific class.
    """
    components = [] # list of components
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for Type in ALL_TYPE_CLASSES:
        if include_deleted:
            comps = list(Type.Component.objects.filter(activity=activity))
        else:
            comps = list(Type.Component.objects.filter(activity=activity, deleted=False))
        components.extend( (c for c in comps if c.id not in found) )
        found.update( (c.id for c in comps) )

    components.sort()
    return components


def select_all_submitted_components(activity):
    submitted_component = [] # list of submitted component
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for Type in ALL_TYPE_CLASSES:
        subs = list(Type.SubmittedComponent.objects.filter(submission__activity = activity))
        submitted_component.extend(s for s in subs if s.id not in found)
        found.update( (s.id for s in subs) )
    submitted_component.sort()
    return submitted_component


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


def get_submission_components(submission, activity, component_list=None):
    """
    return a list of pair[component, latest_submission(could be None)] for specific submission
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

def get_all_submission_components(submission, activity, component_list=None):
    """
    return a list of pair[component, latest_submission(could be None)] for all submissions
    """
    if not component_list:
        component_list = select_all_components(activity)
    
    submitted_components = []
    for component in component_list:
        # find most recent submission for this component
        if submission:
            SubmittedComponent = component.Type.SubmittedComponent
            submits_all = SubmittedComponent.objects.filter(component=component)
            submits = []
            for s in submission:
                submits.extend(submits_all.filter(submission=s))
            if len(submits) > 0:
                submits.sort()
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
    return most recent submission (individual or group) and compilation of valid components
    """
    if activity.group:
        gms = GroupMember.objects.filter(student__person=student, confirmed=True)
        submission = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms)
    else:
        submission = StudentSubmission.objects.filter(activity=activity, member__person=student)

    if len(submission) > 0:
        submitted_components = get_all_submission_components(submission, activity)
        return submission.latest('created_at'), submitted_components
    else:
        submitted_components = get_all_submission_components(None, activity)
        return None, submitted_components

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

def _add_submission_to_zip(zipf, submission, components, prefix=""):
    """
    Add this submission to the zip file, with associated components.
    """
    for component, sub in components:
        if sub:
            sub.add_to_zip(zipf, prefix=prefix)

    # add lateness note
    if submission.created_at > submission.activity.due_date:
        fn = os.path.join(prefix, "LATE.txt")
        zipf.writestr(fn, "Submission was made at %s.\n\nThat is %s after the due date of %s.\n" %
            (submission.created_at, submission.created_at - submission.activity.due_date, submission.activity.due_date))

def generate_activity_zip(activity):
    """
    Return a zip file with all (current) submissions for the activity
    """
    LOGFILE = open("/tmp/ziplog", "a")
    LOGFILE.write("==============================================================")
    LOGFILE.write("activity: "+str(activity))
    LOGFILE.write("\n")
    
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w')
    
    # build dictionary of all most recent submissions by student userid/group slug
    if activity.group:
        submissions = GroupSubmission.objects.filter(activity=activity).order_by('created_at').select_related('activity','group')
    else:
        submissions = StudentSubmission.objects.filter(activity=activity).order_by('created_at').select_related('activity','member','member__person')
    
    # group submissions by student/group
    submissions_by_person = {}
    for s in submissions:
        slug = s.file_slug()
        if slug not in submissions_by_person:
            subs = []
        subs.append(s)
        submissions_by_person[slug] = subs
    
    component_list = select_all_components(activity)
    # now collect submitted components
    for slug in submissions_by_person:
        LOGFILE.write("slug:"+slug+"\n")
        submission = submissions_by_person[slug]
        LOGFILE.write("  subs: "+str(submission)+"\n")
        submitted_components = get_all_submission_components(submission, activity, component_list=component_list)
        LOGFILE.write("  comp: "+str(submitted_components)+"\n")
        _add_submission_to_zip(z, submission[-1], submitted_components, prefix=slug)
    
    z.close()

    file = open(filename, 'rb')
    response = HttpResponse(FileWrapper(file), mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s'% activity.slug + ".zip"
    try:
        os.remove(filename)
    except OSError:
        print "Warning: error removing temporary file."
    return response

def generate_zip_file(submission, submitted_components):
    """
    return a zip file containing latest submission from userid for activity
    """
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w')
    
    _add_submission_to_zip(z, submission, submitted_components)

    z.close()

    file = open(filename, 'rb')
    response = HttpResponse(FileWrapper(file), mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s'% submission.file_slug() + "_" + submission.activity.slug + ".zip"
    try:
        os.remove(filename)
    except OSError:
        print "Warning: error removing temporary file."
    return response

