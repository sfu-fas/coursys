from typing import List, Optional

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.core.files import File
from django.http import QueryDict, HttpResponse
from django.shortcuts import get_object_or_404
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
    'ocaml': 'ocaml',
    'haskell': 'hs',
    'python': 'py',
    'csharp': 'cs',
    'javascript': 'js',
}


def all_code_submissions(activity: Activity) -> List[SubmittedCodefile]:
    """
    Return a list of all files (as SubmittedCodefile instances) for Codefile submissions in this activity.
    """
    si = SubmissionInfo.for_activity(activity)
    si.get_all_components()
    found, individual_subcomps, last_submission = si.most_recent_submissions()
    print(individual_subcomps)
    # flatten submitted component list: https://stackoverflow.com/a/952952
    sub_comps = [c for sublist in si.all_submitted_components for c in sublist]
    # keep only SubmittedCodefiles
    sub_comps = [c for c in sub_comps if c is not None and isinstance(c, SubmittedCodefile)]

    return sub_comps


@transaction.atomic
def run_moss(activity: Activity, language: str) -> SimilarityResult:
    assert language in MOSS_LANGUAGES
    if settings.MOSS_DISTRIBUTION_PATH is None:
        raise ValueError('MOSS_DISTRIBUTION_PATH not set in localsettings')

    moss_pl = os.path.join(settings.MOSS_DISTRIBUTION_PATH, 'moss.pl')
    if not os.path.isfile(moss_pl) or not os.access(moss_pl, os.X_OK):
        raise ValueError('MOSS_DISTRIBUTION_PATH/moss.py is not an executable')

    # get the submissions
    si = SubmissionInfo.for_activity(activity)
    si.get_all_components()
    found, individual_subcomps, last_submission = si.most_recent_submissions()

    #tmpdir = tempfile.TemporaryDirectory()
    #tmp = tmpdir.name
    tmp = '/tmp/foo'
    code_dir = os.path.join(tmp, 'code')
    moss_out_dir = os.path.join(tmp, 'moss')

    # assemble tmp directory of submissions for MOSS
    offering_slug = activity.offering.slug
    extension = '.' + MOSS_LANGUAGES[language]
    moss_files = [] # files that we will give to MOSS
    file_submissions = {} # MOSS input file to submission_id, so we can recover the source later
    for userid, components in individual_subcomps.items():
        prefix = os.path.join(code_dir, offering_slug, userid)
        for comp, sub in components:
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

    # run MOSS
    cmd = [moss_pl, '-l', language, '-o', moss_out_dir, '-m', '100000'] + moss_files
    res = subprocess.run(cmd, cwd=settings.MOSS_DISTRIBUTION_PATH)
    if res.returncode != 0:
        raise RuntimeError('MOSS command failed: ' + str(cmd))

    # save the results, removing any previous MOSS results on this activity
    SimilarityResult.objects.filter(activity=activity, generator='MOSS').delete()
    result = SimilarityResult(activity=activity, generator='MOSS', config={'language': language})
    result.save()

    # try to deal with MOSS' [profanity suppressed] HTML, and produce SimilarityData objects to represent everything
    match_base_re = re.compile(r'^(match\d+)\.html$')
    match_top_re = re.compile(r'^match\d+-top\.html$')
    match_file_re = re.compile(r'^match\d+-\d+\.html$')
    for f in os.listdir(moss_out_dir):
        if f == 'index.html':
            pass

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
                    th.string = th.string.replace(code_dir + '/', '')
            for img in table.find_all('img'):
                src = img.get('src')
                img['src'] = src.replace('../bitmaps/', '/actual_icon_location/')

            file = File(file=io.BytesIO(str(table).encode('utf8')), name=f)
            data = SimilarityData(result=result, label=f, file=file, config={})
            data.save()

        elif match_file_re.match(f):
            data = open(os.path.join(moss_out_dir, f), 'rt', encoding='utf8').read()
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
                img['src'] = src.replace('../bitmaps/', '/actual_icon_location/')

            file = File(file=io.BytesIO(str(pre).encode('utf8')), name=f)
            data = SimilarityData(result=result, label=f, file=file, submission_id=submission_id, config={})
            data.save()

        else:
            raise ValueError('unexpected file produced by MOSS')

    return result


class MOSS(object):
    def __init__(self, offering: CourseOffering, activity: Activity, result: SimilarityResult):
        self.offering = offering
        self.activity = activity
        self.result = result

    def render(self, query: QueryDict) -> Optional[HttpResponse]:
        print(query)
        #match0-top.html match0-0.html match0-1.html

        if 'match' in query: # reconstruct matchX.html
            match = query['match'][0]
            #labels = ['match{}-0.html'.format(match), 'match{}-1.html'.format(match)]
            #data = SimilarityData.objects.filter(result=self.result, label__in=labels).select_related('submission')
            #print(data)

            base = reverse('grades:submission:similarity_result',
                           kwargs={'course_slug': self.offering.slug, 'activity_slug': self.activity.slug, 'result_slug': self.result.generator})

            content = '''<!doctype html><html lang="en"><head><meta charset="utf-8" /><title>???</title></head>
            <frameset rows="150,*"><frameset cols="1000,*"><frame src="{url_top}" name="top" frameborder=0></frameset>
            <frameset cols="50%,50%"><frame src="{url_0}" name="0"><frame src="{url_1}" name="1"></frameset></frameset>
            </html>'''.format(
                url_top=base + '?top=' + str(match),
                url_0=base + '?content=' + str(match) + '_0',
                url_1=base + '?content=' + str(match) + '_1',
            )

        elif 'top' in query: # reconstruct matchX-top.html
            match = query['top'][0]
            data = get_object_or_404(SimilarityData, result=self.result, label='match{}-top.html'.format(match))
            content = data.file.read().decode('utf8')

        else:
            content = '?'

        resp = HttpResponse(content)
        resp.allow_frames_csp = True
        resp.xframe_options_exempt = True
        return resp
