import itertools
from typing import List, Optional

from django import forms
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.core.files import File
from django.http import QueryDict, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, render, get_list_or_404
from django.urls import reverse

from coredata.models import CourseOffering
from grades.models import Activity
from submission.models.codefile import SubmittedCodefile
from submission.models.base import SimilarityResult, SimilarityData
from submission.models import SubmissionInfo
import bs4
import io, os.path, tempfile, subprocess, re


# MOSS language choices. Incomplete: included ones I imagine we might use.
# See @languages in the moss.pl source.
MOSS_LANGUAGES = {  # MOSS language specifier: file extension
    'c': 'c',
    'cc': 'cpp',
    'java': 'java',
    'ruby': 'rb',
    'ml': 'ml',
    'haskell': 'hs',
    'python': 'py',
    'csharp': 'cs',
    'javascript': 'js',
}
MOSS_LANGUAGES_CHOICES = sorted([
    ('c', 'C (*.c)'),
    ('cc', 'C++ (*.cpp)'),
    ('java', 'Java (*.java)'),
    ('ruby', 'Ruby (*.rb)'),
    ('ml', 'OCaml (*.ml)'),
    ('haskell', 'Haskell (*.hs)'),
    ('python', 'Python (*.py)'),
    ('csharp', 'C# (*.cs)'),
    ('javascript', 'JavaScript (*.js)'),
])


class MOSSError(RuntimeError):
    pass


def check_moss_executable(passed, failed):
    if settings.MOSS_DISTRIBUTION_PATH is None:
        failed.append(('MOSS subprocess', 'MOSS_DISTRIBUTION_PATH not set in localsettings'))
        return

    moss_pl = os.path.join(settings.MOSS_DISTRIBUTION_PATH, 'moss.pl')
    if not os.path.isfile(moss_pl) or not os.access(moss_pl, os.X_OK):
        failed.append(('MOSS subprocess', 'MOSS_DISTRIBUTION_PATH/moss.pl is not an executable'))
        return

    passed.append(('MOSS subprocess', 'okay'))


def all_code_submissions(activity: Activity) -> List[SubmittedCodefile]:
    """
    Return a list of all files (as SubmittedCodefile instances) for Codefile submissions in this activity.
    """
    si = SubmissionInfo.for_activity(activity)
    si.get_all_components()
    found, individual_subcomps, last_submission = si.most_recent_submissions()
    # flatten submitted component list: https://stackoverflow.com/a/952952
    sub_comps = [c for sublist in si.all_submitted_components for c in sublist]
    # keep only SubmittedCodefiles
    sub_comps = [c for c in sub_comps if c is not None and isinstance(c, SubmittedCodefile)]

    return sub_comps


def _canonical_filename(filename: str, code_dir: str):
    return filename.replace(code_dir + '/', '')


match_base_re = re.compile(r'^(match(\d+))\.html$')
match_top_re = re.compile(r'^match(\d+)-top\.html$')
match_file_re = re.compile(r'^match(\d+)-([01])\.html$')


@transaction.atomic
def run_moss(main_activity: Activity, activities: List[Activity], language: str, result: SimilarityResult) -> SimilarityResult:
    """
    Run MOSS for the main_activity's submissions.
    ... comparing past submission from everything in the activities list.
    ... looking only at the given programming language.
    ... storing the results in result.
    """
    assert language in MOSS_LANGUAGES
    assert main_activity in activities
    icon_url_path = reverse('dashboard:moss_icon', kwargs={'filename': ''})

    tmpdir = tempfile.TemporaryDirectory()
    tmp = tmpdir.name
    code_dir = os.path.join(tmp, 'code')
    moss_out_dir = os.path.join(tmp, 'moss')

    # assemble tmp directory of submissions for MOSS
    offering_slug = main_activity.offering.slug
    extension = '.' + MOSS_LANGUAGES[language]
    moss_files = [] # files that we will give to MOSS
    file_submissions = {} # MOSS input file to submission_id, so we can recover the source later
    for a in activities:
        si = SubmissionInfo.for_activity(a)
        si.get_all_components()
        _, individual_subcomps, _ = si.most_recent_submissions()
        for userid, components in individual_subcomps.items():
            prefix = os.path.join(code_dir, a.offering.slug, userid)
            for comp, sub in components:
                if not isinstance(sub, SubmittedCodefile):
                    # we can only deal with Codefile components
                    continue
                if not isinstance(sub.code.storage, FileSystemStorage):
                    raise NotImplementedError('more work necessary to support non-filesystem file storage')
                source_file = os.path.join(sub.code.storage.location, sub.code.name)
                moss_file = sub.file_filename(sub.code, prefix)
                if not moss_file.endswith(extension):
                    # we only handle one language at a time
                    continue

                dst_dir, _ = os.path.split(moss_file)
                os.makedirs(dst_dir, exist_ok=True)
                os.symlink(source_file, moss_file)
                moss_files.append(moss_file)
                file_submissions[moss_file] = sub.submission_id

    if not moss_files:
        raise MOSSError('No files found for that language to analyze with MOSS.')

    # run MOSS
    moss_pl = os.path.join(settings.MOSS_DISTRIBUTION_PATH, 'moss.pl')
    cmd = [moss_pl, '-l', language, '-o', moss_out_dir] + moss_files
    try:
        res = subprocess.run(cmd, cwd=settings.MOSS_DISTRIBUTION_PATH)
    except FileNotFoundError:
        raise MOSSError('System not correctly configured with the MOSS executable.')
    if res.returncode != 0:
        raise MOSSError('MOSS command failed: ' + str(cmd))

    # try to deal with MOSS' [profanity suppressed] HTML, and produce SimilarityData objects to represent everything
    for f in os.listdir(moss_out_dir):
        if f == 'index.html':
            data = open(os.path.join(moss_out_dir, f), 'rt', encoding='utf8').read()
            soup = bs4.BeautifulSoup(data, 'lxml')
            index_data = []
            for tr in soup.find_all('tr'):
                if tr.find('th'):
                    continue
                m = []
                for a in tr.find_all('a'):
                    label = a.get('href')
                    fn, perc = a.string.split(' ')
                    fn = _canonical_filename(fn, code_dir)
                    m.append((label, fn, perc))

                # Only display if one side is from the main_activity: leave the past behind.
                if any(fn.startswith(offering_slug+'/') for _,fn,_ in m):
                    index_data.append(m)

            data = SimilarityData(result=result, label='index.html', file=None, config={})
            data.config['index_data'] = index_data
            data.save()

        elif match_base_re.match(f):
            pass

        elif match_top_re.match(f):
            data = open(os.path.join(moss_out_dir, f), 'rt', encoding='utf8').read()
            soup = bs4.BeautifulSoup(data, 'lxml')
            table = soup.find('table')

            del table['bgcolor']
            del table['border']
            del table['cellspacing']
            for th in table.find_all('th'):
                if th.string is not None:
                    th.string = _canonical_filename(th.string, code_dir)
            for img in table.find_all('img'):
                src = img.get('src')
                img['src'] = src.replace('../bitmaps/', icon_url_path)

            file = File(file=io.BytesIO(str(table).encode('utf8')), name=f)
            data = SimilarityData(result=result, label=f, file=file, config={})
            data.save()

        elif match_file_re.match(f):
            try:
                data = open(os.path.join(moss_out_dir, f), 'rt', encoding='utf8').read()
            except UnicodeDecodeError:
                data = open(os.path.join(moss_out_dir, f), 'rt', encoding='windows-1252').read()
            soup = bs4.BeautifulSoup(data, 'lxml')

            # find the input filename, which leads to the submission
            for c in soup.find('body').children:
                if isinstance(c, bs4.element.NavigableString):
                    c = str(c).strip()
                    if c.startswith(code_dir):
                        filename = c
                        break
            submission_id = file_submissions[filename]

            # the only <pre> is the real content we care about
            pre = soup.find('pre')
            for img in pre.find_all('img'):
                src = img.get('src')
                img['src'] = src.replace('../bitmaps/', icon_url_path)

            file = File(file=io.BytesIO(str(pre).encode('utf8')), name=f)
            data = SimilarityData(result=result, label=f, file=file, submission_id=submission_id, config={})
            data.save()

        else:
            raise ValueError('unexpected file produced by MOSS')

    result.config['complete'] = True
    result.save()
    return result


@transaction.atomic
def run_moss_as_task(activities: List[Activity], language: str) -> SimilarityResult:
    """
    Start run_moss() in a Celery task.

    The activities arg: list of all activities to compare with activities[0] being the "main" one for this course.
    """
    # save the results, removing any previous MOSS results on this activity
    activity = activities[0]
    SimilarityResult.objects.filter(activity=activity, generator='MOSS').delete()
    result = SimilarityResult(activity=activity, generator='MOSS', config={'language': language, 'complete': False})
    result.save()

    from submission.tasks import run_moss_task
    run_moss_task.delay(activity.id, [a.id for a in activities], language, result.id)
    return result


class MOSS(object):
    def __init__(self, offering: CourseOffering, activity: Activity, result: SimilarityResult):
        self.offering = offering
        self.activity = activity
        self.result = result

    class CreationForm(forms.Form):
        language = forms.ChoiceField(label='MOSS language', choices=MOSS_LANGUAGES_CHOICES)
        other_offering_activities = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False,
            help_text='Also compare against submissions for these activities from other sections')

    def render(self, request: HttpRequest, path: str) -> HttpResponse:
        if not self.result.config.get('complete'):
            # result still pending in Celery: no other data to find yet
            context = {
                'complete': False,
                'offering': self.offering,
                'activity': self.activity,
                'result': self.result,
            }
            resp = render(request, 'submission/similarity-moss-result.html', context=context)
            return resp

        base_match = match_base_re.match(path)
        top_match = match_top_re.match(path)
        file_match = match_file_re.match(path)

        if base_match: # reconstruct matchX.html
            match = base_match.group(2)

            match0 = get_object_or_404(SimilarityData.objects.select_related('submission'), result=self.result, label='match{}-0.html'.format(match))
            match1 = get_object_or_404(SimilarityData.objects.select_related('submission'), result=self.result, label='match{}-1.html'.format(match))

            sub0, _ = SubmissionInfo._get_submission(match0.submission_id)
            sub1, _ = SubmissionInfo._get_submission(match1.submission_id)

            context = {
                'complete': True,
                'offering': self.offering,
                'activity': self.activity,
                'result': self.result,
                'match_n': match,
                'fn_top': 'match{}-top.html'.format(match),
                'fn_left': 'match{}-0.html'.format(match),
                'fn_right': 'match{}-1.html'.format(match),
                'match0': match0,
                'match1': match1,
                'sub0': sub0,
                'sub1': sub1,
            }
            resp = render(request, 'submission/similarity-moss-result.html', context=context)
            #resp.allow_frames_csp = True
            #resp['X-Frame-Options'] = 'SAMEORIGIN'
            return resp

        elif top_match: # reconstruct matchX-top.html
            match = top_match.group(1)
            data = get_object_or_404(SimilarityData, result=self.result, label='match{}-top.html'.format(match))

        elif file_match: # reconstruct matchX-[01].html
            match = file_match.group(1)
            side = file_match.group(2)
            data = get_object_or_404(SimilarityData, result=self.result, label='match{}-{}.html'.format(match, side))

        else: # index page
            data = SimilarityData.objects.get(result=self.result, label='index.html')
            context = {
                'offering': self.offering,
                'activity': self.activity,
                'result': self.result,
                'data': data,
            }
            resp = render(request, 'submission/similarity-moss.html', context=context)
            return resp

        try:
            content = data.file.read().decode('utf8')
        except FileNotFoundError:
            content = 'missing file'
        resp = HttpResponse(content)
        resp.allow_frames_csp = True
        resp['X-Frame-Options'] = 'SAMEORIGIN'
        return resp
