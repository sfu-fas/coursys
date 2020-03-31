from typing import Dict, Any, TYPE_CHECKING

from django import forms
from django.utils.html import linebreaks, escape
from django.utils.safestring import SafeText, mark_safe

from courselib.markup import MarkupContentField
from quizzes import DEFAULT_QUIZ_MARKUP
if TYPE_CHECKING:
    from quizzes.models import Question, QuestionAnswer


def escape_break(text):
    """
    Helper to display student-entered text reasonably (and safely).
    """
    return mark_safe(linebreaks(escape(text)))


class BaseConfigForm(forms.Form):
    points = forms.IntegerField(min_value=0, max_value=1000, initial=1)
    question = MarkupContentField(label='Question Text', default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

    def to_jsonable(self):
        """
        Convert .cleaned_data to data that will be stored in Question.config.
        """
        return self.cleaned_data


class QuestionHelper(object):
    def __init__(self, question=None):
        self.question = question

    def make_config_form(self, instance: 'Question' = None, data: Dict=None, files: Dict=None) -> BaseConfigForm:
        """
        Returns a Django Form instance that can be used to edit this question's details.

        The Form's 'cleaned_data' should match this question's .config object (unless overriding this method and
        ConfigForm.to_jsonable to deal with differences)
        """
        if instance is None:
            initial = {}
        else:
            initial = instance.config
        return self.ConfigForm(data=data, files=files, initial=initial)

    def get_entry_field(self) -> forms.Field:
        """
        Returns a Django Field for this question, to be filled in by the student.
        """
        raise NotImplementedError()

    def fill_initial(self, field: forms.Field, questionanswer: 'QuestionAnswer'):
        """
        Populate field.initial from the previous QuestionAnswer (used where a student is editing their answer).
        """
        field.initial = questionanswer.answer.get('data', '')

    def to_jsonable(self, cleaned_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert student-submitted cleaned_data (as generated from the .get_entry_field field) to a JSON-friendly format
        that can be stored in QuestionAnswer.answer.
        """
        return {'data': cleaned_data}

    def to_html(self, questionanswer) -> SafeText:
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        raise NotImplementedError
