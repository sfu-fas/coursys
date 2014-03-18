from submission.models.base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput, SelectMultiple
from django import forms
from django.http import HttpResponse
from os.path import splitext
from django.conf import settings
STATIC_URL = settings.STATIC_URL
from django.template import Context, Template


# add file type that should be recognizable when a file is submitted
CODE_TYPES = [
    (".txt", "Plain Text (.txt)"),
    (".java", "Java Source (.java)"),
    (".class", "Java Bytecode (.class)"),
    (".hpp", "C++ Header (.hpp)"),
    (".cpp", "C++ (.cpp)"),
    (".cc", "C++ (.cc)"),
    (".c", "C (.c)"),
    (".h", "C header (.h)"),
    (".py", "Python (.py)"),
    (".rb", "Ruby (.rb)"),
#    (".pl", "Perl (.pl)"),
    (".hs", "Haskell (.hs)"),
    (".pl", "Prolog (.pl)"),
    (".php", "PHP (.php)"),
    (".js", "Javascript (.js)"),
    (".cs", "C# (.cs)"),
    (".html", "HTML (.html)"),
    (".css", "CSS (.css)"),
    (".inc", "HC11 Source (.inc)"),
    (".asm", "HC12 Source (.asm)"),
    (".cct", "Designworks Circuit (.cct)"),
#    (".jpg", "JPEG images (.jpg)"),
    (".json", "JSON data file (.json)"),
    (".go", "Go (.go)"),
    (".m", "MATLAB (.m)"),
    (".mat", "MATLAB data file (.mat)"),
    (".lisp", "LISP (.lisp)"),
    ("Makefile", "Makefile (Makefile)"),
    (".sql", "SQL (.sql)"),
    (".sas", "SAS (.sas)"),
    (".r", "R (.r)"),
    (".dat", "Binary Output (.dat)"),
    (".mdx", "SQL Server Multi-Dimensional Expression (.mdx)"),
    (".clj", "Clojure (.clj)"),
    (".pde", "Processing IDE file (.pde)"),
]
CODE_TYPES = [(desc,ext) for (ext,desc) in CODE_TYPES]
CODE_TYPES.sort()
CODE_TYPES = [(ext,desc) for (desc,ext) in CODE_TYPES]

class CodeComponent(SubmissionComponent):
    "A Source Code submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the Code file, in kB.", null=False, default=2000)
    allowed = models.CharField(max_length=500, null=False, verbose_name='Allowed file types',
                               help_text='Accepted file extensions. [Contact system admins if you need more file types here.]')
    class Meta:
        app_label = 'submission'
    def get_allowed_list(self):
        return self.allowed.split(",")
    def get_allowed_display(self):
        return self.allowed
    def visible_type(self):
        "Soft-delete this type to prevent creation of new"
        return False

class SubmittedCode(SubmittedComponent):
    component = models.ForeignKey(CodeComponent, null=False)
    code = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage,
                            verbose_name='Code submission')

    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.code.url
    def get_size(self):
        try:
            return self.code.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.code.name)[1]

    def download_response(self):
        response = HttpResponse(content_type="text/plain")
        self.sendfile(self.code, response)
        return response
    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.code, prefix)
        zipfile.write(self.code.path, filename)

FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}
			{% if field.errors %}<div class="errortext"><img src="'''+ STATIC_URL+'''icons/error.png" alt="error"/>&nbsp;{{field.errors.0}}</div>{% endif %}
			<div class="helptext">{{field.help_text}}</div>
                    </div>
                </li>''')
                        
class Code:
    label = "code"
    name = "Code"
    descr = "a source code file"
    Component = CodeComponent
    SubmittedComponent = SubmittedCode
    #active = False # depricated in favour of Codefile

    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = CodeComponent
            fields = ['title', 'description', 'max_size', 'allowed', 'specified_filename', 'deleted']
        
        def __init__(self, *args, **kwargs):
            super(Code.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].widget = TextInput(attrs={'style':'width:5em'})
            self.fields['allowed'].widget = SelectMultiple(choices=CODE_TYPES, attrs={'style':'width:40em', 'size': 15})
            self.initial['allowed'] = self._initial_allowed

        def _initial_allowed(self):
            """
            Rework the comma-separated value into a list for the SelectMultiple initial value
            """
            if self.instance:
                return self.instance.allowed.split(',')
            else:
                return []

        def clean_allowed(self):
            data = self.data.getlist('allowed')
            if len(data)==0:
                raise forms.ValidationError("No file types selected")
            return ",".join(data)
     

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedCode
            fields = ['code']
            widgets = {'code': FileInput()}
        def clean_code(self):
            data = self.cleaned_data['code']
            if self.check_is_empty(data):
                raise forms.ValidationError("No file submitted.")
            if not self.check_size(data):
                raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")
            self.check_filename(data)

            # get allowed file types
            upload_ext = splitext(data.name)[1]
            t = CodeComponent.objects.filter(id=self.prefix)
            allowed_list = t[0].allowed.split(",")
            name_okay = False
            if not any([data.name.endswith(ext) for ext in allowed_list]):
                msg = None
                msg_allowed = "Allowed types are:"
                for k in CODE_TYPES:
                    if k[0] in allowed_list:
                        msg_allowed = msg_allowed + " " + k[1] + ","
                    if k[0] == upload_ext:
                        msg = "File extension incorrect.  File appears to be %s." % (k[1])
                if msg is None:
                    msg = "Unable to determine file type (%s)." % upload_ext
                raise forms.ValidationError(msg + " " +msg_allowed[:-1] + ".")
            else:
                return data

SubmittedCode.Type = Code
CodeComponent.Type = Code
