import string
from decimal import Decimal

from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .base import QuestionHelper, BaseConfigForm, MISSING_ANSWER_HTML

OPTION_LETTERS = string.ascii_uppercase


class MultipleChoicesWidget(forms.MultiWidget):
    template_name = 'quizzes/mc_option_widget.html'

    def __init__(self, n=10, *args, **kwargs):
        self.n = n
        choice_widgets = [
            forms.TextInput(attrs={'class': 'mc-choice'})
            for _ in range(self.n)
        ]
        mark_widgets = [
            forms.TextInput(attrs={'class': 'mc-mark'})
            for _ in range(self.n)
        ]
        super().__init__(widgets=(choice_widgets + mark_widgets), *args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)

        # rearrange the subwidgets to we can display them appropriately
        subwidgets = context['widget']['subwidgets']
        choice_widgets = [w for w in subwidgets if w['attrs']['class'] == 'mc-choice']
        mark_widgets = [w for w in subwidgets if w['attrs']['class'] == 'mc-mark']

        context['widget_sets'] = zip(OPTION_LETTERS, choice_widgets, mark_widgets)
        return context

    def decompress(self, value):
        if value is None:
            return ['' for _ in range(self.n)] + ['0' for _ in range(self.n)]
        else:
            return value


class MultipleChoicesField(forms.MultiValueField):
    widget = MultipleChoicesWidget

    def __init__(self, n=10, required=True, *args, **kwargs):
        self.n = n
        self.require_one = required
        fields = [
            forms.CharField(required=False, max_length=1000, initial='')
            for _ in range(self.n)
        ]
        fields += [
            forms.DecimalField(required=False, initial=0)
            for _ in range(self.n)
        ]
        super().__init__(fields=fields, require_all_fields=False, required=False, *args, **kwargs)
        self.force_display_required = True

    def compress(self, data_list):
        options = data_list[:self.n]
        marks = data_list[self.n:]
        options = zip(options, marks)
        options = [(o, str(m)) for o, m in options if o]
        return options

    def prepare_value(self, value):
        if value is None:
            return None
        elif len(value) == 2 * self.n:
            return value

        initial = ['' for _ in range(self.n)] + ['0' for _ in range(self.n)]
        if value is not None:
            options = [o for o,m in value]
            initial[0:len(options)] = options
            marks = [m for o,m in value]
            initial[self.n:len(marks)+self.n] = marks
        return initial

    def clean(self, value):
        choices = super().clean(value)
        if len(choices) < 2:
            raise forms.ValidationError('Must give at least two options.')
        options = [o for o,_ in choices]
        if len(options) != len(set(options)):
            raise forms.ValidationError('Choices must be unique')
        return choices


permutation_choices = [
    ('keep', 'Keep the order as-is'),
    ('permute', 'Randomly permute the choices'),
    ('not-last', 'Randomly permute, except the last choice should stay last'),
]


class MultipleChoice(QuestionHelper):
    name = 'Multiple Choice'
    NA = '' # value used to represent "no answer"
    auto_markable = True

    # A MC question's options field is a list of pairs (option_text, marks) where option_text is shown to the student,
    # and marks is the worth of that answer when automarking.

    class ConfigForm(BaseConfigForm):
        options = MultipleChoicesField(required=True, label='Options and marks', help_text='Options presented to students, with number of marks to assign with auto-marking. Any options left blank will not be displayed.')
        permute = forms.ChoiceField(required=True, choices=permutation_choices, help_text='You will still see the answers as they are above: a student answer of \u201CA\u201D refers to the first choice above, regardless of the order they see.')

        def clean(self):
            data = self.cleaned_data
            if 'points' in data and 'options' in data:
                points = data['points']
                marks = [float(m) for o,m in data['options']]
                if max(marks) > points:
                    raise forms.ValidationError('Auto-marking value greater than question max points.')
                if min(marks) < -points:
                    raise forms.ValidationError('Auto-marking penalty greater than question total max points.')
            return data

    def get_entry_field(self, questionanswer=None, student=None):
        options = self.version.config.get('options', [])
        permute = self.version.config.get('permute', 'keep')
        if questionanswer:
            initial = questionanswer.answer.get('data', MultipleChoice.NA)
        else:
            initial = MultipleChoice.NA

        options = list(enumerate(options))  # keep original positions so the input values match that, but students see a possibly-randomized order

        if student and permute == 'permute':
            rand = self.question.quiz.random_generator(str(student.id) + '-' + str(self.question.id) + '-' + str(self.version.id))
            options = rand.permute(options)
        elif student and permute == 'not-last':
            rand = self.question.quiz.random_generator(str(student.id) + '-' + str(self.question.id) + '-' + str(self.version.id))
            last = options[-1]
            choices = rand.permute(options[:-1])
            choices.append(last)

        choices = [
            (OPTION_LETTERS[opos], mark_safe('<span class="mc-letter">' + OPTION_LETTERS[i] + '.</span> ') + escape(o[0]))
            for i, (opos, o)
            in enumerate(options)
        ]

        choices.append((MultipleChoice.NA, 'no answer'))

        field = forms.ChoiceField(required=False, initial=initial, choices=choices, widget=forms.RadioSelect())
        field.widget.attrs.update({'class': 'multiple-choice'})
        return field

    def to_text(self, questionanswer):
        ans = questionanswer.answer.get('data', MultipleChoice.NA)
        if ans == MultipleChoice.NA:
            return 'no answer'
        else:
            return ans

    def to_html(self, questionanswer):
        ans = questionanswer.answer.get('data', MultipleChoice.NA)
        if ans == MultipleChoice.NA:
            return MISSING_ANSWER_HTML
        else:
            return ans

    def question_preview_html(self):
        # override to present options (original order) along with question text
        options = self.version.config.get('options', [])
        q_html = self.question_html()
        choices_html = [
            '<p><span class="mc-letter">%s.</span> %s</p>' % (OPTION_LETTERS[i], escape(o[0]))
            for i, o
            in enumerate(options)
        ]
        return mark_safe(''.join((
            '<div>',
            q_html,
            ''.join(choices_html),
            '</div>'
        )))

    def automark(self, questionanswer):
        ans = questionanswer.answer.get('data')
        if ans and ans in OPTION_LETTERS:
            i = OPTION_LETTERS.index(ans)
            mark = Decimal(self.version.config['options'][i][1])
            return mark, ''
        else:
            return Decimal(0), ''
