import base64
import hashlib
import os.path
import random
import string
import urllib

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.forms import ClearableFileInput
from django.shortcuts import resolve_url
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe

from quizzes.types.base import QuestionHelper, BaseConfigForm, MISSING_ANSWER_HTML
from submission.models.codefile import FILENAME_TYPES, validate_filename

FILE_SECRET_LENGTH = 32


def new_file_secret():
    """
    A random secret for unauth access to uploaded files
    """
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(FILE_SECRET_LENGTH))


class CleanClearableFileInput(ClearableFileInput):
    template_name = 'quizzes/clean_clearable_file_input.html'

    def format_value(self, value):
        # format as just the filename
        if value and value.name:
            _, filename = os.path.split(value.name)
            return filename
        else:
            return 'none'

    def value_from_datadict(self, data, files, name):
        # override to accept the case "clear + file upload" without ValidationError
        upload = super().value_from_datadict(data, files, name)
        if not self.is_required and forms.CheckboxInput().value_from_datadict(
                data, files, self.clear_checkbox_name(name)):

            #if upload:
            #    return FILE_INPUT_CONTRADICTION

            # False signals to clear any existing value, as opposed to just None
            return False
        return upload


class FileAnswerField(forms.FileField):
    widget = CleanClearableFileInput

    def __init__(self, max_size: int, filename: str, filename_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_size = max_size
        self.filename = filename
        self.filename_type = filename_type

    def clean(self, data, initial=None):
        cleaned = super().clean(data)
        if cleaned and cleaned.size > self.max_size:
            raise forms.ValidationError('Submitted files can be at most %i bytes in size.' % (self.max_size,))
        return cleaned


class FileAnswer(QuestionHelper):
    name = 'File Upload'

    class ConfigForm(BaseConfigForm):
        max_size = forms.IntegerField(initial=10000, min_value=0, max_value=settings.MAX_SUBMISSION_SIZE, help_text='Maximum file size that can be uploaded by the student, in kilobytes.')
        filename = forms.CharField(max_length=500, required=False, help_text='Required filename for submitted files. Interpreted as specified in the filename type. Blank for no restriction.')
        filename_type = forms.ChoiceField(choices=FILENAME_TYPES, required=True, initial='EXT', help_text='How should your filename be interpreted?')

    def get_entry_field(self, questionanswer=None, student=None):
        max_size = self.version.config.get('max_size', 10000)
        filename = self.version.config.get('filename', '')
        filename_type = self.version.config.get('filename_type', 'EXT')

        if questionanswer:
            initial = questionanswer.file
        else:
            initial = None

        field = FileAnswerField(required=False, max_length=100, max_size=max_size, filename=filename,
                                filename_type=filename_type, initial=initial,
                                validators=[lambda upfile: validate_filename(filename, filename_type, upfile.name)])
        field.widget.attrs.update({'class': 'file-answer'})
        return field

    def to_jsonable(self, cleaned_data):
        data = {}
        if isinstance(cleaned_data, UploadedFile):
            data['filename'] = cleaned_data.name
            data['size'] = cleaned_data.size
            data['content-type'] = cleaned_data.content_type
            data['charset'] = cleaned_data.charset
            data['secret'] = new_file_secret()
            h = hashlib.sha256()
            for c in cleaned_data.chunks(1000):
                h.update(c)
            data['sha256'] = h.hexdigest()
        return {'data': data, '_file': cleaned_data}

    @staticmethod
    def unchanged_answer(prev_ans, new_ans):
        return (new_ans['_file'] is None
                or ('sha256' in prev_ans['data'] and 'sha256' in new_ans['data']
                        and prev_ans['data']['sha256'] == new_ans['data']['sha256'])
        )

    def secret_url(self, questionanswer):
        return settings.BASE_ABS_URL + resolve_url(
            'offering:quiz:submitted_file',
            course_slug=self.question.quiz.activity.offering.slug,
            activity_slug=self.question.quiz.activity.slug,
            userid=questionanswer.student.person.userid_or_emplid(),
            answer_id=questionanswer.id,
            secret=questionanswer.answer['data'].get('secret', '?')
        )

    def to_text(self, questionanswer):
        data = questionanswer.answer['data']
        if 'filename' in data and 'secret' in data:
            return self.secret_url(questionanswer)
        else:
            return None

    def to_html(self, questionanswer):
        data = questionanswer.answer['data']
        if 'filename' in data and 'secret' in data:
            html = '<p><a href="%s">%s</a> (%s)</p>' % (
                self.secret_url(questionanswer),
                data['filename'],
                filesizeformat(data['size']),
            )
        else:
            html = MISSING_ANSWER_HTML
        return mark_safe(html)

    # unused but maybe useful later?
    def to_data_url(self, questionanswer):
        size = questionanswer.answer['data']['size']
        if size < 1024 * 10:
            data = questionanswer.file.read()
            parts = [
                'data:',
                urllib.parse.quote(questionanswer.answer['data']['content-type']),
                ';base64,',
                urllib.parse.quote(base64.b64encode(data).decode('ascii'))
            ]
            content = ''.join(parts)
        else:
            content = 'file %i bytes, type %s' % (size, questionanswer.answer['data']['content-type'])
        return content
