import datetime
from typing import List

from django import forms

from coredata.models import Member
from courselib.markup import MarkupContentField, MarkupContentMixin
from grades.models import Activity
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.models import Quiz, TimeSpecialCase


class QuizTimeBaseForm(forms.ModelForm):
    start = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    end = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    start.widget.widgets[0].attrs.update({'class': 'datepicker'})
    end.widget.widgets[0].attrs.update({'class': 'datepicker'})

    def clean(self):
        cleaned_data = super().clean()

        start = self.cleaned_data.get('start')
        end = self.cleaned_data.get('end')
        if start and end and start >= end:
            raise forms.ValidationError("Quiz cannot end before it starts.")

        return cleaned_data


class QuizForm(MarkupContentMixin(field_name='intro'), QuizTimeBaseForm):
    intro = MarkupContentField(required=False, label='Introductory Text (displayed at the top of the quiz)', default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

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


class TimeSpecialCaseForm(QuizTimeBaseForm):
    class Meta:
        model = TimeSpecialCase
        fields = ['student', 'start', 'end']
        widgets = {}

    def __init__(self, quiz: Quiz, students: List[Member], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz
        self.fields['student'].choices = [(m.id, "%s (%s, %s)" % (m.person.sortname(), m.person.userid, m.person.emplid)) for m in students]

    def clean(self):
        cleaned_data = super().clean()
        # must have the quiz where we're editing
        self.instance.quiz = self.quiz
        return cleaned_data

    def clean_student(self):
        student = self.cleaned_data['student']
        # ensure uniqueness of the quiz/student pair
        if TimeSpecialCase.objects.filter(quiz=self.quiz, student=student).exists():
            raise forms.ValidationError('This student already has a special case: you must delete it before adding another.')
        return student
