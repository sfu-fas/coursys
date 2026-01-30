
import os
from string import Template
import tempfile
from typing import Iterable, Optional
import zipfile
from django import forms
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
import urllib
from coredata.models import CourseOffering
from grades.models import Activity
from submission.models import SubmissionInfo
from submission.models.base import SimilarityResult
from submission.models.codefile import SubmittedCodefile


# see https://github.com/jplag/JPlag/releases
JPLAG_RELEASE_URL = 'https://github.com/jplag/JPlag/releases/download/v6.3.0/jplag-6.3.0-jar-with-dependencies.jar'

JPLAG_JAR_FILENAME = 'jplag-6.3.0-jar-with-dependencies.jar'
JPLAG_CACHE_FILE = f'/tmp/{JPLAG_JAR_FILENAME}'

# JPlag language choices. Incomplete: included ones I imagine we might use.
# See https://github.com/jplag/JPlag?tab=readme-ov-file#supported-languages
JPLAG_LANGUAGES = {  # MOSS language specifier: file extension
    'java': 'java',
    'c': 'c',
    'cc': 'cpp',
    'csharp': 'cs',
    'python3': 'py',
    'javascript': 'js',
    'typescript': 'ts',
    'golang': 'go',
    'kotlin': 'kt',
    'rlang': 'r',
    'rust': 'rs',
    'swift': 'swift',
    'scala': 'scala',
    'scheme': 'scm',
}
JPLAG_LANGUAGES_CHOICES = sorted([
    ('java', 'Java (*.java)'),
    ('c', 'C (*.c)'),
    ('cc', 'C++ (*.cpp)'),
    ('csharp', 'C# (*.cs)'),
    ('python3', 'Python 3 (*.py)'),
    ('javascript', 'JavaScript (*.js)'),
    ('typescript', 'TypeScript (*.ts)'),
    ('golang', 'Go (*.go)'),
    ('kotlin', 'Kotlin (*.kt)'),
    ('rlang', 'R (*.r)'),
    ('rust', 'Rust (*.rs)'),
    ('swift', 'Swift (*.swift)'),
    ('scala', 'Scala (*.scala)'),
    ('scheme', 'Scheme (*.scm)'),
])



class JPlagError(RuntimeError):
    def __init__(self, message: str, extra: Optional[str] = None):
        super().__init__(message)
        self.extra = extra


class JPlag(object):
    def __init__(self, offering: CourseOffering, activity: Activity, result: SimilarityResult):
        self.offering = offering
        self.activity = activity
        self.result = result

    class CreationForm(forms.Form):
        tool = forms.CharField(initial='jplag', widget=forms.HiddenInput())
        language = forms.ChoiceField(label='JPlag language', choices=JPLAG_LANGUAGES_CHOICES)
        other_offering_activities = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False,
            help_text='Also compare against submissions for these activities from other sections')


def get_jplag_jar():
    if not os.path.isfile(JPLAG_CACHE_FILE):
        print("FETCHING JAR")
        with urllib.request.urlopen(JPLAG_RELEASE_URL) as req, open(JPLAG_CACHE_FILE, 'wb') as jarfile:
            assert req.status == 200
            jar = req.read()
            jarfile.write(jar)
            return jar
    else:
        with open(JPLAG_CACHE_FILE, 'rb') as jarfile:
            return jarfile.read()


README_TEMPLATE = Template("""# JPlag Instructions

You can run JPlag and view its results with this command:
```sh
$cmd
```
If you have distributed partial solutions or template code, put it into the `base-code` directory
and use this command:
```sh
$bccmd
```

For more options, see the [JPlag README](https://github.com/jplag/JPlag).
""")


def build_jplag_zip(activities: Iterable[Activity], language: str) -> str:
    """
    Build a .zip file with everything needed to run JPlag.
    Returns filename of a temp file that somebody else must delete.
    """
    extension = '.' + JPLAG_LANGUAGES[language]
    base_dir = f'jplag-{activities[0].slug}'
    code_dir = f'{base_dir}/code'
    tmp = tempfile.NamedTemporaryFile(delete=False)
    
    with zipfile.ZipFile(tmp.name, "w") as zip:
        # prep general ZIP contents
        zip.writestr(f"{base_dir}/base-code/", "")
        zip.writestr(f"{base_dir}/{JPLAG_JAR_FILENAME}", get_jplag_jar())
        cmd = f"java -jar {JPLAG_JAR_FILENAME} --language={language} code/*"
        bccmd = f"java -jar {JPLAG_JAR_FILENAME} --language={language} --base-code=base-code code/*"
        zip.writestr(f"{base_dir}/README.md", README_TEMPLATE.substitute(cmd=cmd, bccmd=bccmd))

        # assemble all of the code files
        for a in activities:
            si = SubmissionInfo.for_activity(a)
            si.get_all_components()
            _, individual_subcomps, _ = si.most_recent_submissions()
            for userid, components in individual_subcomps.items():
                prefix = os.path.join(code_dir, a.offering.slug, userid)
                for _, sub in components:
                    if not isinstance(sub, SubmittedCodefile):
                        # we can only deal with Codefile components
                        continue
                    if not isinstance(sub.code.storage, FileSystemStorage):
                        raise NotImplementedError('more work necessary to support non-filesystem file storage')
                    
                    source_file = os.path.join(sub.code.storage.location, sub.code.name)
                    bundle_file = sub.file_filename(sub.code, prefix)
                    if not bundle_file.endswith(extension):
                        # we only handle one language at a time
                        continue

                    zip.write(source_file, arcname=bundle_file)

    return tmp.name
