from typing import Dict, Any

from django import forms
from django.utils.safestring import SafeText

from courselib.markup import MarkupContentField
from quizzes import DEFAULT_QUIZ_MARKUP


class BaseConfigForm(forms.Form):
    points = forms.IntegerField(min_value=0, max_value=1000)
    question = MarkupContentField(label='Question Text', default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

    def to_jsonable(self):
        return self.cleaned_data


class QuestionType(object):
    def __init__(self):
        pass

    def make_config_form(self, instance=None, data=None, files=None, initial=None) -> BaseConfigForm:
        """
        Returns a Django Form instance that can be used to edit this question's details.

        The Form's 'cleaned_data' should match this question's 'config' object.
        """
        return self.ConfigForm(data=data, files=files, initial=initial)

    def make_entry_field(self, questionanswer=None) -> forms.Field:
        """
        Returns a Django Field for this question, to be filled in by the student. If questionanswer is given, it is
        a QuestionAnswer instance that must be used to populate initial data in the field.
        """
        raise NotImplementedError()

    def serialize_field(self, field) -> Dict[str, Any]:
        """
        Convert filled field (as returned by .make_entry_field) to a JSON-friendly format that can be stored in
        QuestionAnswer.answer
        """
        raise NotImplementedError()

    def to_html(self, questionanswer=None) -> SafeText:
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        raise NotImplementedError
