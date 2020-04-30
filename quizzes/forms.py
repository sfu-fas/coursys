from typing import List, Optional

from django import forms
from django.utils.safestring import mark_safe

from coredata.models import Member
from courselib.markup import MarkupContentField, MarkupContentMixin
from grades.models import Activity
from marking.models import StudentActivityMark, ActivityComponentMark, ActivityComponent
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
    grace = forms.IntegerField(required=True, min_value=0, max_value=3600, initial=300, label='Grace time',
                               help_text=mark_safe('Number of seconds after the &ldquo;true&rdquo; end of the quiz that '
                                                   'students may submit their answers (but not reload the quiz to continue working).'))
    intro = MarkupContentField(required=False, label='Introductory Text (displayed at the top of the quiz, optional)',
                               default_markup=DEFAULT_QUIZ_MARKUP, with_wysiwyg=True)

    class Meta:
        model = Quiz
        fields = ['start', 'end']
        widgets = {}

    def __init__(self, activity: Activity, instance: Optional[Quiz] = None, *args, **kwargs):
        self.activity = activity
        super().__init__(instance=instance, *args, **kwargs)
        if instance:
            self.initial['grace'] = instance.grace

    def clean(self):
        cleaned_data = super().clean()
        # all Quiz instances must have the activity where we're editing
        self.instance.activity = self.activity
        self.instance.grace = cleaned_data['grace']
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


class ComponentForm(forms.ModelForm):
    class Meta:
        model = ActivityComponentMark
        fields = ['value', 'comment']

    def __init__(self, component: ActivityComponent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.component = component


class MarkingSetupForm(forms.Form):
    delete_others = forms.BooleanField(required=False, initial=False)


class MarkingForm(forms.ModelForm):
    class Meta:
        model = StudentActivityMark
        fields = ['late_penalty', 'mark_adjustment', 'mark_adjustment_reason', 'overall_comment']
        widgets = {}

    def __init__(self, activity: Activity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.activity = activity

    def save(self, commit=True, *args, **kwargs):
        am = super().save(commit=False)

        return super().save(commit=commit, *args, **kwargs)
