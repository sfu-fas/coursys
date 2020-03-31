from django import forms

from courselib.markup import MarkupContentField, MarkupContentMixin
from grades.models import Activity
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.models import Quiz


class QuizForm(MarkupContentMixin(field_name='intro'), forms.ModelForm):
    start = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    end = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    intro = MarkupContentField(label='Introductory Text (displayed at the top of the quiz)', default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

    start.widget.widgets[0].attrs.update({'class': 'datepicker'})
    end.widget.widgets[0].attrs.update({'class': 'datepicker'})

    class Meta:
        model = Quiz
        fields = ['start', 'end']
        widgets = {}

    def __init__(self, activity: Activity, *args, **kwargs):
        self.activity = activity
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # all Quiz instances must have the activity where we're editing
        self.instance.activity = self.activity
        return cleaned_data


class StudentForm(forms.Form):
    # fields for student responses will be filled dynamically in the view
    pass
