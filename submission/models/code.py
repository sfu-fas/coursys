from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput, SelectMultiple
from django import forms
from django.http import HttpResponse
from os.path import splitext
from settings import MEDIA_URL
from django.template import Context, Template


# add file type that should be recognizable when a file is submitted
CODE_TYPES = [
    (".txt", "Plain Text (.txt)"),
    (".java", "Java Source (.java)"),
    (".class", "Java Bytecode (.class)"),
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
    (".cct", "Designworks Circuit (.cct)"),
#    (".jpg", "JPEG images (.jpg)"),
    (".json", "JSON data file (.json)"),
]

class CodeComponent(SubmissionComponent):
    "A Source Code submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the Code file, in kB.", null=False, default=2000)
    allowed = models.CharField(max_length=500, null=False, help_text='Accepted file extensions. [Contact system admins if you need more file types here.]')
    # allowed_types = {} # not in use
    class Meta:
        app_label = 'submission'
    def get_allowed_list(self):
        return self.allowed.split(",")


class SubmittedCode(SubmittedComponent):
    component = models.ForeignKey(CodeComponent, null=False)
    code = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage)

    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.code.url
    def get_size(self):
        try:
            return self.image.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.code.name)[1]

    def download_response(self):
        response = HttpResponse(mimetype="text/plain")
        self.sendfile(self.code, response)
        return response
    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.code, prefix)
        zipfile.write(self.code.path, filename)

FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}
			{% if field.errors %}<div class="errortext"><img src="'''+ MEDIA_URL+'''icons/error.png" alt="error"/>&nbsp;{{field.errors.0}}</div>{% endif %}
			<div class="helptext">{{field.help_text}}</div>
                    </div>
                </li>''')
                        
class Code:
    label = "code"
    name = "Code"
    Component = CodeComponent
    SubmittedComponent = SubmittedCode

    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = CodeComponent
            fields = ['title', 'description', 'max_size', 'allowed', 'deleted', 'specified_filename']
        
        def __init__(self, *args, **kwargs):
            super(Code.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].widget = TextInput(attrs={'style':'width:5em'})
            self.fields['max_size'].label=mark_safe("Max size"+submission.forms._required_star)

            self.fields['allowed'].widget = SelectMultiple(choices=CODE_TYPES, attrs={'style':'width:40em', 'size': 15})
            self.initial['allowed'] = self._initial_allowed
            self.fields['allowed'].label=mark_safe("Allowed Types"+submission.forms._required_star)

            self.fields['deleted'].label=mark_safe("Invisible")

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
            
        # output a customized form as <li>
        def custom_form(self, text="Submit"):
            # uncomment next line to see original form
            return None
            
            output = ['<p class="requireindicator"><img src="'+MEDIA_URL+'icons/required_star.gif" alt="required" />&nbsp;indicates required field</p>']
            output.append("<ul>")
            for field in self:
                if field.name is "allowed":
                    output.append("""
                                <li>
                                    <label for="id_allowed">Allowed File Types</label>
                                    <div class="inputfield">
                                    <select id="id_allowed" class="multiselect" multiple="multiple" name="allowed" >
                    """)
                    
                    # get field value
                    # see http://code.djangoproject.com/ticket/10427
                    t = Template("{% load submission_filters %}{{field|display_value}}")
                    c = Context({"field":field})
                    selected_list = t.render(c).split(",")
                    
                    # when form submitted with error, '&#39;' are somehow added to the strings in the list... 
                    new_list = []
                    for i in selected_list:
                        ii = i.split('&#39;')
                        for ki in ii:
                            if ki.startswith("."):
                                new_list.append(ki)
                    selected_list = new_list
                    # print selected_list

                    for k in CODE_TYPES:
                        output.append('<option value="' + k[0] + '"')
                        if k[0] in selected_list:
                            output.append('selected="selected"')
                        output.append(">" + k[1] +" (" + k[0] + ")</option>")

                    output.append("""
                                    </select>""")
                    output.append('''<div class="errortext">''')
                    if field.errors:
                        output.append('''<img src="'''+ MEDIA_URL +'''icons/error.png" alt="error"/>&nbsp;''' + field.errors[0] + '</div>')
                    output.append('''<div class="helptext">
                                    </div>
                                    </div>
                                </li>
                    ''')
                else:
                    c = Context({"field":field})
                    output.append( FIELD_TEMPLATE.render(c) )
            output.append('<li><input class="submit" type="submit" value="'+text+'" /></li>\n</ul>')
            return mark_safe('\n'.join(output))

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
            
            if upload_ext not in allowed_list:
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
