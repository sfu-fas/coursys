from typing import Dict, Any, TYPE_CHECKING

from django import forms
from django.utils.html import linebreaks, escape
from django.utils.safestring import SafeText, mark_safe

from courselib.markup import MarkupContentField, markup_to_html
from quizzes import DEFAULT_QUIZ_MARKUP
if TYPE_CHECKING:
    from quizzes.models import Question, QuestionAnswer


def escape_break(text: str) -> SafeText:
    """
    Helper to display student-entered text reasonably (and safely).
    """
    return mark_safe(linebreaks(escape(text)))


class BaseConfigForm(forms.Form):
    points = forms.IntegerField(min_value=0, max_value=1000, initial=1)
    text = MarkupContentField(label='Question Text', required=True, default_markup=DEFAULT_QUIZ_MARKUP,
                                  with_wysiwyg=True, restricted=True)

    def to_jsonable(self):
        """
        Convert .cleaned_data to data that will be stored in Question.config.
        """
        return self.cleaned_data


class QuestionHelper(object):
    name: str

    def __init__(self, question=None, version=None):
        #assert question or hasattr(version, 'question_cached') or hasattr(version, '_question_cache'), "Question must be given explicitly, or QuestionVersion's .question must be pre-fetched with select_related."
        assert not question or not version or version.question_id == question.id, 'question/version mismatch'
        if question:
            self.question = question
        else:
            self.question = version.question
        self.version = version

    def make_config_form(self, data: Dict[str, Any] = None, files: Dict = None) -> BaseConfigForm:
        """
        Returns a Django Form instance that can be used to edit this question's details.

        The Form's 'cleaned_data' should match this QuestionVersion.config object (unless overriding this method and
        ConfigForm.to_jsonable to deal with differences)
        """
        if self.version is None:
            initial = {}
        else:
            initial = self.version.config

        if self.version.question:
            initial['points'] = self.question.points

        form = self.ConfigForm(data=data, files=files, initial=initial)
        if self.question.id:
            form.fields['points'].help_text = 'Changing this will update all versions of this question.'
        return form

    def question_html(self) -> SafeText:
        text, markup, math = self.version.text
        return markup_to_html(text, markup, math=math)

    def question_preview_html(self) -> SafeText:
        return self.question_html()

    def get_entry_field(self, questionanswer: 'QuestionAnswer' = None, student: 'Member' = None) -> forms.Field:
        """
        Returns a Django Field for this question, to be filled in by the student.

        If questionanswer is given, its .answer contents must be used to set the field's initial value.
        If student is given, it can be used to customize the question for that student (e.g. permuting MC answers)
        """
        raise NotImplementedError()

    def to_jsonable(self, cleaned_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert student-submitted cleaned_data (as generated from the .get_entry_field field) to a JSON-friendly format
        that can be stored in QuestionAnswer.answer.

        If returned, the dict key '_file' must be a django.core.files.uploadedfile.UploadedFile instance, and will
        be moved to QuestionAnswer.file when saving.
        """
        return {'data': cleaned_data}

    @staticmethod
    def unchanged_answer(prev_ans: Dict[str, Any], new_ans: Dict[str, Any]) -> bool:
        """
        Is the newly-submitted answer (new_ans) unchanged from the old (prev_ans)? Both in the format returned by
        .to_jsonable().
        """
        return prev_ans == new_ans

    def to_html(self, questionanswer) -> SafeText:
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        # default is good enough for plain-text-ish things.
        return escape_break(self.to_text(questionanswer))

    def to_text(self, questionanswer) -> str:
        """
        Convert QuestionAnswer to plain for JSON output.
        """
        raise NotImplementedError
