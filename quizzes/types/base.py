from typing import Dict, Any

from django import forms
from django.utils.safestring import SafeText

from courselib.markup import MarkupContentField
from quizzes import DEFAULT_QUIZ_MARKUP


class BaseConfigForm(forms.Form):
    points = forms.IntegerField(min_value=0, max_value=1000, initial=1)
    question = MarkupContentField(label='Question Text', default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

    def to_jsonable(self):
        return self.cleaned_data


class QuestionHelper(object):
    def __init__(self, question=None):
        self.question = question

    def make_config_form(self, instance=None, data=None, files=None, initial=None) -> BaseConfigForm:
        """
        Returns a Django Form instance that can be used to edit this question's details.

        The Form's 'cleaned_data' should match this question's 'config' object.
        """
        return self.ConfigForm(data=data, files=files, initial=initial)

    def get_entry_field(self, questionanswer=None) -> forms.Field:
        """
        Returns a Django Field for this question, to be filled in by the student. If questionanswer is given, it is
        a QuestionAnswer instance that must be used to populate initial data in the field.
        """
        raise NotImplementedError()

    def to_jsonable(self, cleaned_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert submitted cleaned_data (as generated from the .get_entry_field field) to a JSON-friendly format that
        can be stored in QuestionAnswer.answer.
        """
        return {'data': cleaned_data}

    def fill_initial(self, field: forms.Field, questionanswer):
        field.initial = questionanswer.answer.get('data', '')

    def to_html(self, questionanswer=None) -> SafeText:
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        raise NotImplementedError
