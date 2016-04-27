import zipfile
import tempfile
import os
import errno
import StringIO
import unicodecsv as csv
from pipes import quote
from datetime import datetime

from django.core.servers.basehttp import FileWrapper
from django.http import StreamingHttpResponse

from base import SubmissionComponent, Submission, StudentSubmission, GroupSubmission, SubmittedComponent
from coredata.models import Person
from groups.models import GroupMember

from url import URL
from archive import Archive
from pdf import PDF
from code import Code
from word import Word
from image import Image
from office import Office
from codefile import Codefile
from gittag import GitTag
from text import Text

ALL_TYPE_CLASSES = [Archive, Code, Codefile, GitTag, Image, Office, PDF, Text, URL, Word]

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
            comps = list(Type.Component.objects.filter(activity_id=activity.id))
        else:
            comps = list(Type.Component.objects.filter(activity_id=activity.id, deleted=False))
        components.extend( (c for c in comps if c.id not in found) )
        found.update( (c.id for c in comps) )

    components.sort()
    return components


def select_all_submitted_components(activity_id):
    submitted_component = [] # list of submitted component
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for Type in ALL_TYPE_CLASSES:
        subs = list(Type.SubmittedComponent.objects.filter(submission__activity_id=activity_id))
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


class SubmissionInfo(object):
    """
    Collection of information about a student's/group's submission.

    self.components and self.submitted_components will always correspond, so can be zipped.
    """
    def __init__(self, activity, student=None, include_deleted=False):
        self.include_deleted = include_deleted
        self.activity = activity
        self.student = student
        assert student is None or isinstance(student, Person)

        self.components = None
        self.submissions = None

        if student:
            if self.activity.group:
                gms = GroupMember.objects.filter(student__person=student, confirmed=True, activity=activity)
                self.is_group = True
                self.submissions = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms)
            else:
                self.is_group = False
                self.submissions = StudentSubmission.objects.filter(activity=activity, member__person=student)

            self.submissions = self.submissions.order_by('-created_at')


    @classmethod
    def from_submission_id(cls, submission_id):
        submission, is_group = cls._get_submission(submission_id)
        activity = submission.activity
        si = cls(activity=activity)
        if submission:
            si.submissions = [submission]
        else:
            si.submissions = []

        si.is_group = is_group
        si.get_most_recent_components()

        return si


    @staticmethod
    def _get_submission(submission_id):
        try:
            return StudentSubmission.objects.get(id=submission_id), False
        except StudentSubmission.DoesNotExist:
            try:
                return GroupSubmission.objects.get(id=submission_id), True
            except GroupSubmission.DoesNotExist:
                return None, None


    def have_submitted(self):
        return bool(self.submissions)

    def latest(self):
        return self.submissions[0]

    def components_and_submitted(self):
        """
        Iterable of (SubmissionComponent, SubmittedComponent|None) pairs
        """
        self.ensure_components()
        assert self.submitted_components is not None
        return zip(self.components, self.submitted_components)

    def ensure_components(self):
        """
        Make sure self.component_list is populated.
        """
        if self.components:
            return
        self.components = select_all_components(self.activity, include_deleted=self.include_deleted)

    def get_most_recent_components(self):
        """
        Build self.submitted_components by taking the most-recently-submitted for each component.
        Relevant to single-submit behaviour.
        """
        self.ensure_components()

        submitted_components = []
        for component in self.components:
            SubmittedComponent = component.Type.SubmittedComponent
            submits = SubmittedComponent.objects.filter(component=component, submission__in=self.submissions).order_by('-submit_time')
            if submits:
                sub = submits[0]
            else:
                # this component has never been submitted
                sub = None
            submitted_components.append(sub)

        self.submitted_components = submitted_components

    def generate_zip_file(self):
        self.ensure_components()
        assert self.submissions
        assert self.submitted_components is not None

        handle, filename = tempfile.mkstemp('.zip')
        os.close(handle)
        z = zipfile.ZipFile(filename, 'w')

        self._add_to_zip(z, self.activity, self.components_and_submitted(), self.submissions[0].created_at, slug=self.submissions[0].file_slug())

        z.close()

        file = open(filename, 'rb')
        response = StreamingHttpResponse(FileWrapper(file), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="%s_%s.zip"' % (
                self.submissions[0].file_slug(), self.activity.slug)
        try:
            os.remove(filename)
        except OSError:
            pass
        return response

    @staticmethod
    def _add_to_zip(zipf, activity, components_and_submitted, created_at, prefix='', slug=None):
        for component, subcomp in components_and_submitted:
            if subcomp:
                try:
                    subcomp.add_to_zip(zipf, prefix=prefix, slug=slug)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # Missing file? How did that come up once in five years?
                        fn = os.path.join(prefix, "MISSING_FILE.txt")
                        zipf.writestr(fn, "A file named '%s' was submitted but can't be found on CourSys. That's weird.\n"
                                          "Please email coursys-help@sfu.ca and ask us to help track it down."
                                      % (subcomp.get_filename()))
                    else:
                        raise

        # add lateness note
        if activity.due_date and created_at > activity.due_date:
            fn = os.path.join(prefix, "LATE.txt")
            zipf.writestr(fn, "Submission was made at %s.\n\nThat is %s after the due date of %s.\n" %
                          (created_at, created_at - activity.due_date, activity.due_date))


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



def generate_submission_contents(activity, z, prefix=''):
    """
    add of of the submissions for this activity to the ZipFile z
    """
    from submission.models.gittag import GitTagComponent
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
            submissions_by_person[slug] = []
        subs = submissions_by_person[slug]
        subs.append(s)
    
    component_list = select_all_components(activity, include_deleted=True)
    sub_time = {} # submission times for summary
    # Manage a collection of git tag submission data we see, to produce clone-all script.
    any_git_tags = any(isinstance(c, GitTagComponent) for c in component_list)
    git_tags = []
    # now collect submitted components (and last-submission times for summary)
    for slug in submissions_by_person:
        submission = submissions_by_person[slug]
        last_sub = max([s.created_at for s in submission])
        sub_time[slug] = last_sub
        submitted_components = get_all_submission_components(submission, activity, component_list=component_list)
        _add_submission_to_zip(z, submission[-1], submitted_components, prefix=prefix+slug, slug=slug)
        git_tags.extend((comp.slug, slug, sub.url, sub.tag) for comp, sub in submitted_components if isinstance(comp, GitTagComponent) and sub)

    # produce summary of submission datetimes
    slugs = sub_time.keys()
    slugs.sort()
    summarybuffer = StringIO.StringIO()
    summarycsv = csv.writer(summarybuffer)
    summarycsv.writerow([Person.userid_header(), "Last Submission"])
    for s in slugs:
        summarycsv.writerow([s, sub_time[s].strftime("%Y/%m/%d %H:%M:%S")])
    z.writestr(prefix+"summary.csv", summarybuffer.getvalue())
    summarybuffer.close()

    # produce git clone-all script
    if any_git_tags:
        script = ['#!/bin/sh', '', '# This script will clone all of the submitted git tags for this activity,',
                '# putting them into the current directory. This should work in a Linux, OSX,',
                '# or the Git Bash shell in Windows.', '']

        git_tags.sort()
        for comp_slug, sub_slug, url, tag in git_tags:
            dir_name = comp_slug + '_' + sub_slug
            script.append('git clone %s %s && \\\n  (cd %s && git checkout tags/%s)' % (quote(url), quote(dir_name), quote(dir_name), quote(tag)))

        script.append('')
        z.writestr(prefix+"clone-all.sh", '\n'.join(script))


def generate_activity_zip(activity, prefix=''):
    """
    Return a zip file with all (current) submissions for the activity
    """
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w')
    
    generate_submission_contents(activity, z, prefix=prefix)
    z.close()

    file = open(filename, 'rb')
    response = StreamingHttpResponse(FileWrapper(file), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s.zip"' % (activity.slug)
    try:
        os.remove(filename)
    except OSError:
        pass
    return response
