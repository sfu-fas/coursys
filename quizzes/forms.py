import datetime

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

        start = self.cleaned_data.get('start')
        end = self.cleaned_data.get('end')
        if start and end and start >= end:
            raise forms.ValidationError("Quiz cannot end before it starts.")

        return cleaned_data

    def clean_end(self):
        end = self.cleaned_data['end']
        if end <= datetime.datetime.now():
            raise forms.ValidationError("Quiz must end in the future.")
        return end


class StudentForm(forms.Form):
    # fields for student responses will be filled dynamically in the view
    pass
