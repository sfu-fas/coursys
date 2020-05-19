from typing import Tuple

from django import forms
from django.utils.html import escape, linebreaks
from django.utils.safestring import mark_safe

from courselib.codemirror_language_list import CODEMIRROR_MODES, HIGHLIGHT_SUBSTITUTIONS
from courselib.markup import MarkupContentField, markup_to_html
from submission.models.livecode import LANGUAGE_CHOICES
from .base import QuestionHelper, BaseConfigForm, MISSING_ANSWER_HTML


class ShortAnswer(QuestionHelper):
    name = 'Short Answer'

    class ConfigForm(BaseConfigForm):
        max_length = forms.IntegerField(required=True, min_value=1, max_value=1000, initial=500, label='Maximum length',
                                        help_text='Maximum number of characters the students can enter when answering.')

    def get_entry_field(self, questionanswer=None, student=None):
        max_length = self.version.config.get('max_length', 1000)
        if questionanswer:
            initial = questionanswer.answer.get('data', '')
        else:
            initial = None

        field = forms.CharField(required=False, max_length=max_length, initial=initial)
        field.widget.attrs.update({'class': 'short-answer'})
        return field

    def to_text(self, questionanswer):
        return questionanswer.answer.get('data', '')

    def to_html(self, questionanswer):
        ans = questionanswer.answer.get('data', '')
        if ans:
            return mark_safe('<p>' + escape(ans) + '</p>')
        else:
            return MISSING_ANSWER_HTML


class LongAnswer(QuestionHelper):
    name = 'Long Answer'

    class ConfigForm(BaseConfigForm):
        max_length = forms.IntegerField(required=True, min_value=100, max_value=100000, initial=10000, label='Maximum length',
                                        help_text='Maximum number of characters the students can enter when answering.')
        lines = forms.IntegerField(required=True, min_value=2, max_value=40, initial=10,
                                   help_text=mark_safe('Number of lines the students will see in the field when answering: this does <strong>not</strong> limit the length of their answer'))

    def get_entry_field(self, questionanswer=None, student=None):
        max_length = self.version.config.get('max_length', 10000)
        lines = self.version.config.get('lines', 5)
        if questionanswer:
            initial = questionanswer.answer.get('data', '')
        else:
            initial = None

        field = forms.CharField(required=False, max_length=max_length, initial=initial,
                                widget=forms.Textarea(attrs={'rows': lines, 'cols': 100}))
        field.widget.attrs.update({'class': 'long-answer'})
        return field

    def to_text(self, questionanswer):
        return questionanswer.answer.get('data', '')

    def to_html(self, questionanswer):
        ans = questionanswer.answer.get('data', '')
        if ans:
            return mark_safe(linebreaks(ans, autoescape=True))
        else:
            return MISSING_ANSWER_HTML


class CodeAnswer(LongAnswer):
    class ConfigForm(LongAnswer.ConfigForm):
        language = forms.ChoiceField(required=True, label='Programming Language',
                                    choices=LANGUAGE_CHOICES,
                                    help_text='Syntax highlighting that will be used in the entry box.')

    def get_entry_field(self, questionanswer=None, student=None):
        field = super().get_entry_field(questionanswer=questionanswer, student=student)
        field.widget.attrs.update({'class': 'code-answer', 'data-mode': self.version.config.get('language', '')})
        return field

    def entry_head_html(self):
        lang = self.version.config.get('language')
        if lang:
            url = [url for mode, label, url in CODEMIRROR_MODES if mode == lang][0]
            return mark_safe('<script src="%s"></script>' % (url,))
        else:
            return mark_safe('')

    def to_html(self, questionanswer):
        ans = questionanswer.answer.get('data', '')
        if ans:
            cm_lang = self.version.config.get('language')
            hl_lang = HIGHLIGHT_SUBSTITUTIONS.get(cm_lang, cm_lang)
            return mark_safe('<pre class="code-answer language-%s">%s</pre>' % (hl_lang, escape(ans)))
        else:
            return MISSING_ANSWER_HTML


class FormattedAnswer(QuestionHelper):
    name = 'Long Answer with formatting'
    default_initial = ('', 'html-wysiwyg', False)

    class ConfigForm(BaseConfigForm):
        max_length = forms.IntegerField(required=True, min_value=100, max_value=100000, initial=10000, label='Maximum length',
                                        help_text='Maximum number of characters the students can enter when answering.')
        lines = forms.IntegerField(required=True, min_value=5, max_value=30, initial=10,
                                   help_text=mark_safe('Number of lines the students will see in the field when answering: this does <strong>not</strong> limit the length of their answer'))
        #math = forms.BooleanField(required=False, initial=False, help_text='Should answers be formatted with LaTeX formulas (when displayed?')

    def get_entry_field(self, questionanswer=None, student=None):
        max_length = self.version.config.get('max_length', 10000)
        lines = self.version.config.get('lines', 10)
        if questionanswer:
            initial = (questionanswer.answer.get('data', FormattedAnswer.default_initial))
        else:
            initial = FormattedAnswer.default_initial

        if initial[1] == 'html':
            # turn on HTML WYSIWYG by default if we're working with HTML
            initial[1] = 'html-wysiwyg'

        field = MarkupContentField(required=False, max_length=max_length, rows=lines, with_wysiwyg=True,
                                   restricted=True, default_markup='html-wysiwyg', allow_math=False,
                                   initial=initial)
        field.widget.attrs.update({'class': 'formatted-answer'})
        return field

    def to_jsonable(self, cleaned_data):
        # We'll always store sanitized HTML as our "answer" for "formatted" questions.
        # Other markup languages are converted here, before storage.
        text, markup, math = cleaned_data
        return {'data': [text, markup, False]}

    def to_html(self, questionanswer):
        return self.to_text(questionanswer)

    def to_text(self, questionanswer):
        # our "text" representation is the HTML of the response
        text, markup, math = questionanswer.answer.get('data', FormattedAnswer.default_initial)
        if text:
            html = markup_to_html(text, markup, math=None, restricted=True)
            return html
        else:
            return MISSING_ANSWER_HTML

    @staticmethod
    def unchanged_answer(prev_ans, new_ans):
        # normalize 'html' and 'html-wysiwyg' formatting choice
        prev_data = prev_ans['data']
        new_data = new_ans['data']
        if prev_data[1] == 'html':
            prev_data = [prev_data[0], 'html-wysiwyg', prev_data[2]]
        if new_data[1] == 'html':
            new_data = [new_data[0], 'html-wysiwyg', new_data[2]]
        return prev_data == new_data


class NumericAnswer(QuestionHelper):
    name = 'Numeric Answer'

    class ConfigForm(BaseConfigForm):
        resp_type = forms.ChoiceField(required=True, choices=[('float', 'Real number'), ('int', 'Integer')],
                                      label='Response Type', help_text='Type of number the students can enter.')

    def get_entry_field(self, questionanswer=None, student=None):
        resp_type = self.question.config.get('resp_type', 'float')
        if questionanswer:
            initial = questionanswer.answer.get('data', '')
        else:
            initial = None

        if resp_type == 'int':
            field = forms.IntegerField(required=False, initial=initial)
        else:
            field = forms.FloatField(required=False, initial=initial)

        field.widget.attrs.update({'class': 'numeric-answer'})
        return field

    def to_text(self, questionanswer):
        return questionanswer.answer.get('data', None)

    def to_html(self, questionanswer):
        ans = questionanswer.answer.get('data', None)
        if ans:
            return mark_safe('<p>' + escape(ans) + '</p>')
        else:
            return MISSING_ANSWER_HTML
