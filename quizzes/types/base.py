from collections import OrderedDict
from decimal import Decimal
from typing import Dict, Any, TYPE_CHECKING, Tuple, Optional

from django import forms
from django.utils.datastructures import MultiValueDict
from django.utils.html import linebreaks, escape
from django.utils.safestring import SafeText, mark_safe

from courselib.markup import MarkupContentField, markup_to_html, MARKUPS
from quizzes import DEFAULT_QUIZ_MARKUP
if TYPE_CHECKING:
    from quizzes.models import Question, QuestionAnswer


MISSING_ANSWER_HTML = mark_safe('<p class="empty">[No answer.]</p>')


def escape_break(text: str) -> SafeText:
    """
    Helper to display student-entered text reasonably (and safely).
    """
    return mark_safe(linebreaks(escape(text)))


class BaseConfigForm(forms.Form):
    points = forms.IntegerField(min_value=0, max_value=1000, initial=1)
    text = MarkupContentField(label='Question Text', required=True, default_markup=DEFAULT_QUIZ_MARKUP,
                                  with_wysiwyg=True, restricted=True)
    marking = MarkupContentField(label='Marking Notes (visible only to instructors/TAs when marking, optional)',
                                 required=False, default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True, restricted=True,
                                 rows=10)
    review = MarkupContentField(label='Review Notes (visible to students when reviewing quiz, optional)',
                                required=False, default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True, restricted=True,
                                rows=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # reorder the fields, so marking and review are last
        fields = self.fields
        # this code assumes dicts are insertion ordered, which they are in Python 3.7+ https://stackoverflow.com/a/39980744/6871666
        new_fields = fields.__class__()
        for f in fields:
            if f in ['marking', 'review']:
                continue
            new_fields[f] = fields[f]
        new_fields['marking'] = fields['marking']
        new_fields['review'] = fields['review']
        self.fields = new_fields

    def to_jsonable(self):
        """
        Convert .cleaned_data to data that will be stored in Question.config.
        """
        return self.cleaned_data


class QuestionHelper(object):
    #name: str
    auto_markable = False  # can this question type be auto-marked? Must implement automark() if so.

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

    def config_to_form(self, data: Dict[str, Any], points: Decimal) -> Dict[str, Any]:
        """
        Convert a QuestionVersion.config value back to a corresponding request.POST style dict, so we can validate
        JSON imports using existing for validators.

        Will likely need to override this if .ConfigForm has validators that change the data as part of the cleaning.
        """
        text = data['text']
        formdata = MultiValueDict({k: [v] for k,v in data.items() if k != 'text'})
        formdata['text_0'] = text[0]
        formdata['text_1'] = text[1]
        formdata['text_2'] = text[2]
        formdata['points'] = points
        return formdata

    def process_import(self, data: Dict[str, Any], points: Decimal) -> Dict[str, Any]:
        """
        Convert the export format (a Version.config) into a Version.config, except validating that everything is legal.

        Raises forms.ValidationError if there are problems. Returns a valid Version.config if not.
        """
        if 'text' not in data:
            raise forms.ValidationError(' missing "text"')
        text = data['text']
        if not (
                isinstance(text, list) and len(text) == 3
                and isinstance(text[0], str)
                and isinstance(text[1], str) and text[1] in MARKUPS
                and isinstance(text[2], bool)
        ):
            raise forms.ValidationError('["text"] must be a triple of (text, markup_language, math_bool).')

        formdata = self.config_to_form(data, points)
        form = self.make_config_form(data=formdata, files=None)
        if not form.is_valid():
            # If there are errors, pick one and report it.
            error_dict = form.errors
            field = list(error_dict.keys())[0]
            error = error_dict[field][0]
            raise forms.ValidationError('["%s"]: %s' % (field, error))

        del form.cleaned_data['points']
        return form.cleaned_data

    def question_html(self) -> SafeText:
        text, markup, math = self.version.text
        return markup_to_html(text, markup, math=math, hidden_llm=True)

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

    def to_html(self, questionanswer: 'QuestionAnswer') -> SafeText:
        """
        Convert QuestionAnswer to HTML for display to the user.
        """
        # default is good enough for plain-text-ish things.
        return escape_break(self.to_text(questionanswer))

    def to_text(self, questionanswer: 'QuestionAnswer') -> str:
        """
        Convert QuestionAnswer to plain for JSON output.
        """
        raise NotImplementedError

    def is_blank(self, questionanswer: 'QuestionAnswer') -> bool:
        """
        Is this answer "blank"?
        """
        raise NotImplementedError

    def entry_head_html(self) -> SafeText:
        return mark_safe('')

    def automark(self, questionanswer: 'QuestionAnswer') -> Optional[Tuple[Decimal, str]]:
        """
        Return marking data for this question: mark (presumably out of the question's max points) and comment.

        Return None if question is not markable.
        """
        return None
