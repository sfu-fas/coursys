from django.conf import settings
from django.core.files.storage import FileSystemStorage
from submission.models.codefile import SubmittedCodefile
from submission.models import SubmissionInfo
import os.path, tempfile, subprocess


# MOSS language choices. Incomplete: included ones I imagine we might use.
# See @languages in the moss.pl source.
MOSS_LANGUAGES = { # MOSS language specifier: file extension
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


def all_code_submissions(activity):
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


def run_moss(activity, language):
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

    #tmp = tempfile.TemporaryDirectory()
    tmp = '/tmp/foo'
    code_dir = os.path.join(tmp, 'code')
    moss_out_dir = os.path.join(tmp, 'moss')

    # assemble tmp directory of submissions for MOSS
    offering_slug = activity.offering.slug
    extension = '.' + MOSS_LANGUAGES[language]
    moss_files = []
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

    # run MOSS
    cmd = [moss_pl, '-l', language, '-o', moss_out_dir, '-m', '100000'] + moss_files
    print(' '.join(cmd))
    res = subprocess.run(cmd, cwd=settings.MOSS_DISTRIBUTION_PATH)
    if res.returncode != 0:
        raise RuntimeError('MOSS command failed: ' + str(cmd))

    # try to deal with MOSS' [profanity supressed] HTML
    from bs4 import BeautifulSoup
    data = open(os.path.join(moss_out_dir, 'match0-0.html'), 'rt', encoding='utf8').read()
    soup = BeautifulSoup(data, 'lxml')
    print(soup.find('title').string.replace(code_dir + '/', ''))
    print(soup.find('pre'))

