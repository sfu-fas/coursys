from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .base import QuestionHelper, BaseConfigForm

OPTION_LETTERS = 'ABCDEFGHIJKLMNOP'


class MCOptionInput(forms.TextInput):
    # subclass so the text input knows its position and it can be rendered appropriately
    def __init__(self, position, *args, **kwargs):
        super().__init__(attrs={'class': 'mc-option-input'}, *args, **kwargs)
        self.position = position

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        context['widget']['letter'] = OPTION_LETTERS[self.position]
        return context


class MultipleTextWidget(forms.MultiWidget):
    template_name = 'quizzes/mc_option_widget.html'

    def __init__(self, n=10, *args, **kwargs):
        self.n = n
        widgets = [
            MCOptionInput(position=i)
            for i in range(self.n)
        ]
        super().__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        if value is None:
            return ['' for _ in range(self.n)]
        else:
            return value


class MultipleTextField(forms.MultiValueField):
    widget = MultipleTextWidget

    def __init__(self, n=10, required=True, *args, **kwargs):
        self.n = n
        self.require_one = required
        fields = [
            forms.CharField(required=False, max_length=1000, initial='')
            for _ in range(self.n)
        ]
        super().__init__(fields=fields, require_all_fields=False, required=False, *args, **kwargs)
        self.force_display_required = True

    def compress(self, data_list):
        options = [d for d in data_list if d != '']
        if len(options) < 2:
            raise forms.ValidationError('Must give at least two options.')
        return options


class MultipleChoice(QuestionHelper):
    name = 'Multiple Choice'
    NA = '' # value used to represent "no answer"

    class ConfigForm(BaseConfigForm):
        options = MultipleTextField(required=True, help_text='Options presented to students. Any left blank will not be displayed.')

    def get_entry_field(self, questionanswer=None):
        options = self.question.config.get('options', [])
        if questionanswer:
            initial = questionanswer.answer.get('data', MultipleChoice.NA)
        else:
            initial = MultipleChoice.NA

        choices = [
            (OPTION_LETTERS[i], mark_safe('<span class="mc-letter">' + OPTION_LETTERS[i] + '.</span> ') + escape(o))
            for i, o
            in enumerate(options)
        ]
        choices.append((MultipleChoice.NA, 'no answer'))

        field = forms.ChoiceField(required=False, initial=initial, choices=choices, widget=forms.RadioSelect())
        field.widget.attrs.update({'class': 'multiple-choice'})
        return field

    def to_text(self, questionanswer):
        return questionanswer.answer.get('data', MultipleChoice.NA)
