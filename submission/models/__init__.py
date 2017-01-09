import zipfile
import tempfile
import os
import errno
import StringIO
import unicodecsv as csv
from pipes import quote
from datetime import datetime

from wsgiref.util import FileWrapper
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

    # Constructors

    def __init__(self, activity, student=None, include_deleted=False):
        self.include_deleted = include_deleted
        self.activity = activity
        self.student = student
        assert student is None or isinstance(student, Person)

        self.components = None
        self.submissions = None
        self.submitted_components = None
        self.all_submitted_components = None
        self.is_group = self.activity.group

        if student:
            if self.activity.group:
                gms = GroupMember.objects.filter(student__person=student, confirmed=True, activity=activity).select_related('group')
                if gms:
                    self.group = gms[0].group
                self.submissions = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms).select_related('group')
            else:
                self.submissions = StudentSubmission.objects.filter(activity=activity, member__person=student).select_related('member__person')

            self.submissions = self.submissions.order_by('-created_at')


    @classmethod
    def from_submission_id(cls, submission_id):
        """
        Build for a specific submission
        """
        submission, is_group = cls._get_submission(submission_id)
        if not submission:
            raise ValueError, 'No such submission'

        activity = submission.activity
        si = cls(activity=activity)
        si.is_group = is_group
        si.submissions = [submission]

        if is_group:
            si.group = submission.group
            si.student = None
        else:
            si.student = submission.member.person

        si.get_most_recent_components()

        return si

    @classmethod
    def for_activity(cls, activity):
        """
        Gather info for a whole class on the activity.
        """
        si = cls(activity=activity)

        if si.activity.group:
            si.submissions = GroupSubmission.objects.filter(activity=activity)
        else:
            si.submissions = StudentSubmission.objects.filter(activity=activity)

        si.submissions = si.submissions.order_by('-created_at')

        return si




    # Utility methods

    @staticmethod
    def _get_submission(submission_id):
        try:
            return StudentSubmission.objects.get(id=submission_id), False
        except StudentSubmission.DoesNotExist:
            try:
                return GroupSubmission.objects.get(id=submission_id), True
            except GroupSubmission.DoesNotExist:
                return None, None


    # State-updating methods

    def ensure_components(self):
        """
        Make sure self.component_list is populated.

        Fills self.components.
        """
        if self.components:
            return
        self.components = select_all_components(self.activity, include_deleted=self.include_deleted)

    def get_most_recent_components(self):
        """
        Find the most-recently-submission for each component.

        Fills self.submitted_components.
        """
        if self.submitted_components is not None:
            return

        self.ensure_components()

        submitted_components = []
        for component in self.components:
            SubmittedComponent = component.Type.SubmittedComponent
            submits = SubmittedComponent.objects.filter(component=component,
                    submission__in=self.submissions).order_by('-submit_time')
            if submits:
                sub = submits[0]
            else:
                # this component has never been submitted
                sub = None
            submitted_components.append(sub)

        self.submitted_components = submitted_components

    def get_all_components(self):
        """
        Collected all submitted components (for self.submissions) by finding all submissions for each component.

        Fills self.all_submitted_components.

        self.all_submitted_components and self.submissions correspond, so can be zipped.
        self.all_submitted_components[i] and self.components correspond, so can be zipped.
        """
        if self.all_submitted_components is not None:
            return

        self.ensure_components()
        assert self.submissions is not None

        # build dict-of-dicts to map submission -> component -> submittedcomponent
        subcomps = {s.id: {} for s in self.submissions}

        for component in self.components:
            SubmittedComponent = component.Type.SubmittedComponent
            scs = SubmittedComponent.objects.filter(component=component,
                    submission__in=self.submissions).order_by('-submission__created_at').select_related('submission')
            for sc in scs:
                sub = subcomps[sc.submission.id]
                sub[sc.component.id] = sc

        self.all_submitted_components = []
        for s in self.submissions:
            scs = []
            for c in self.components:
                scs.append(subcomps.get(s.id, {}).get(c.id, None))
            self.all_submitted_components.append(scs)


    # Status/read-state methods

    def have_submitted(self):
        return bool(self.submissions)

    def latest(self):
        return self.submissions[0]

    def components_and_submitted(self):
        """
        Iterable of (SubmissionComponent, SubmittedComponent|None) pairs for most-recent submissions
        """
        self.ensure_components()
        assert self.submitted_components is not None
        return zip(self.components, self.submitted_components)

    def submissions_and_components(self):
        """
        Iterable of (Submission, [(SubmissionComponent, SubmittedComponent|None)]) pairs
        """
        assert self.submissions is not None
        assert self.all_submitted_components is not None
        for sub, subcomps in zip(self.submissions, self.all_submitted_components):
            yield sub, zip(self.components, subcomps)

    def all_components_and_submitted(self):
        """
        Iterable of (SubmissionComponent, SubmittedComponent|None) pairs for all submissions
        """
        assert self.submissions is not None
        assert self.all_submitted_components is not None

        for sub, subcomps in zip(self.submissions, self.all_submitted_components):
            for pr in zip(self.components, subcomps):
                yield pr

    def accessible_by(self, request):
        """
        Can we show this info the the user?
        """
        assert self.submissions is not None
        from courselib.auth import is_course_staff_by_slug

        if request.user.is_anonymous():
            return False

        elif is_course_staff_by_slug(request, self.activity.offering.slug):
            return True

        elif self.is_group:
            membership = self.group.groupmember_set.filter(
                student__person__userid=request.user.username, activity=self.activity, confirmed=True)
            return membership.exists()

        else:
            return self.student.userid == request.user.username

    def generate_student_zip(self):
        self.ensure_components()
        assert self.submissions

        multi = self.activity.multisubmit()

        if multi:
            self.get_all_components()
            compsub = self.all_components_and_submitted()
        else:
            self.get_most_recent_components()
            compsub = self.components_and_submitted()

        handle, filename = tempfile.mkstemp('.zip')
        os.close(handle)
        z = zipfile.ZipFile(filename, 'w')

        self._add_to_zip(z, self.activity, compsub, self.submissions[0].created_at,
                slug=self.submissions[0].file_slug(), multi=multi)

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

    def generate_activity_zip(self):
        """
        Create ZIP file for this activity
        """
        handle, filename = tempfile.mkstemp('.zip')
        os.close(handle)

        z = zipfile.ZipFile(filename, 'w')
        self.generate_submission_contents(z, prefix='')
        z.close()

        file = open(filename, 'rb')
        response = StreamingHttpResponse(FileWrapper(file), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="%s.zip"' % (self.activity.slug)
        try:
            os.remove(filename)
        except OSError:
            pass

        return response

    @staticmethod
    def _add_to_zip(zipf, activity, components_and_submitted, created_at, prefix='', slug=None, multi=False):
        """
        Add this list of (SubmissionComponent, SubmittedComponent) pairs to the zip file.
        """
        for component, subcomp in components_and_submitted:
            if subcomp:
                if multi:
                    dt = subcomp.submission.created_at.strftime('%Y-%m-%d-%H-%M-%S')
                    p = os.path.join(prefix, dt)
                else:
                    p = prefix

                try:
                    subcomp.add_to_zip(zipf, prefix=p, slug=slug)
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

    def generate_submission_contents(self, z, prefix='', always_summary=True):
        """
        Assemble submissions and put in ZIP file.
        """
        self.ensure_components()
        assert self.submissions is not None
        assert self.all_submitted_components is not None

        multi = self.activity.multisubmit()

        from submission.models.gittag import GitTagComponent
        any_git_tags = any(isinstance(c, GitTagComponent) for c in self.components)
        git_tags = []

        # Collect all of the SubmittedComponents that we need to output
        # i.e. the most recent of each by student|group and component
        found = set()  # (student|group, SubmissionComponent) pairs we have already included
        individual_subcomps = {}  # student|group: [(SubmissionComponent, SubmittedComponent)]
        last_submission = {}  # student|group: final Submission
        for sub, subcomps in self.submissions_and_components():
            slug = sub.file_slug()
            for comp, sc in subcomps:
                key = (slug, comp.slug)
                if (not multi and key in found) or sc is None:
                    continue

                if slug not in last_submission:
                    last_submission[slug] = sub

                found.add(key)

                scs = individual_subcomps.get(slug, [])
                scs.append((comp, sc))

                individual_subcomps[sub.file_slug()] = scs

        # Now add them to the ZIP
        for slug, subcomps in individual_subcomps.iteritems():
            lastsub = last_submission[slug]
            p = os.path.join(prefix, slug)
            self._add_to_zip(z, self.activity, subcomps, lastsub.created_at,
                    slug=lastsub.file_slug(), prefix=p, multi=multi)

            git_tags.extend((comp.slug, slug, sub.url, sub.tag) for comp, sub in subcomps if
                            isinstance(comp, GitTagComponent) and sub)

        # produce summary of submission datetimes
        if found or always_summary:
            slugs = last_submission.keys()
            slugs.sort()
            summarybuffer = StringIO.StringIO()
            summarycsv = csv.writer(summarybuffer)
            summarycsv.writerow([Person.userid_header(), "Last Submission"])
            for s in slugs:
                summarycsv.writerow([s, last_submission[s].created_at.strftime("%Y/%m/%d %H:%M:%S")])
            z.writestr(prefix + "summary.csv", summarybuffer.getvalue())
            summarybuffer.close()

        # produce git clone-all script
        if any_git_tags:
            script = ['#!/bin/sh', '', '# This script will clone all of the submitted git tags for this activity,',
                      '# putting them into the current directory. This should work in a Linux, OSX,',
                      '# or the Git Bash shell in Windows.', '']

            git_tags.sort()
            for comp_slug, sub_slug, url, tag in git_tags:
                dir_name = comp_slug + '_' + sub_slug
                script.append('git clone %s %s && \\\n  (cd %s && git checkout tags/%s)' % (
                    quote(url), quote(dir_name), quote(dir_name), quote(tag)))

            script.append('')
            z.writestr(prefix + "clone-all.sh", '\n'.join(script))

