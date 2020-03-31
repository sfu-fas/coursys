from django import forms
from django.utils.safestring import mark_safe

from .base import QuestionHelper, BaseConfigForm, escape_break


class ShortAnswer(QuestionHelper):
    name = 'Short Answer'

    class ConfigForm(BaseConfigForm):
        max_length = forms.IntegerField(required=True, min_value=1, max_value=1000, initial=500, label='Maximum length',
                                        help_text='Maximum number of characters the students can enter when answering.')

    def get_entry_field(self):
        max_length = self.question.config.get('max_length', 1000)
        field = forms.CharField(required=False, max_length=max_length)
        field.widget.attrs.update({'class': 'short-answer'})
        return field

    def to_html(self, questionanswer):
        text = questionanswer.answer.get('data', '')
        return escape_break(text)


class MediumAnswer(QuestionHelper):
    name = 'Medium Answer'

    class ConfigForm(BaseConfigForm):
        max_length = forms.IntegerField(required=True, min_value=100, max_value=10000, initial=1000, label='Maximum length',
                                        help_text='Maximum number of characters the students can enter when answering.')
        lines = forms.IntegerField(required=True, min_value=1, max_value=10, initial=3,
                                   help_text=mark_safe('Number of lines the students will see in the field when answering: this does <strong>not</strong> limit the length of their answer'))

    def get_entry_field(self):
        max_length = self.question.config.get('max_length', 10000)
        lines = self.question.config.get('lines', 3)
        field = forms.CharField(required=False, max_length=max_length, widget=forms.Textarea(attrs={'rows': lines, 'cols': 100}))
        field.widget.attrs.update({'class': 'medium-answer'})
        return field

    def to_html(self, questionanswer):
        text = questionanswer.answer.get('data', '')
        return escape_break(text)
