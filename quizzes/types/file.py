from django import forms
from django.conf import settings

from quizzes.types.base import QuestionHelper, BaseConfigForm
from submission.models.codefile import FILENAME_TYPES


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
        # TODO: validators for those

        if questionanswer:
            initial = questionanswer.file
        else:
            initial = None

        field = forms.FileField(required=False, max_length=100, initial=initial)
        field.widget.attrs.update({'class': 'file-answer'})
        return field

    def to_jsonable(self, cleaned_data):
        return {'data': {}, '_file': cleaned_data}

    def to_text(self, questionanswer):
        raise NotImplementedError
