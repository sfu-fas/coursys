import decimal
import json
from decimal import Decimal
from typing import List, Optional

from django import forms
from django.utils.safestring import mark_safe

from coredata.models import Member
from courselib.markup import MarkupContentField, MarkupContentMixin, MARKUPS
from grades.models import Activity
from marking.models import StudentActivityMark, ActivityComponentMark, ActivityComponent
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.models import Quiz, TimeSpecialCase, QUESTION_HELPER_CLASSES, Question, QuestionVersion


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
    honour_code = forms.BooleanField(required=False, initial=True, help_text="Require students to agree to the honour code before they can proceed with the quiz?")
    photo_verification = forms.BooleanField(required=False, initial=True, help_text="Require students to take a photo with their webcam when submitting the quiz?")
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
            self.initial['honour_code'] = instance.honour_code
            self.initial['photo_verification'] = instance.photos

    def clean(self):
        cleaned_data = super().clean()
        # all Quiz instances must have the activity where we're editing
        self.instance.activity = self.activity
        self.instance.grace = cleaned_data['grace']
        self.instance.honour_code = cleaned_data['honour_code']
        self.instance.photos = cleaned_data['photo_verification']
        return cleaned_data


class StudentForm(forms.Form):
    # fields for student responses will be filled dynamically in the view
    pass


class QuizImportForm(forms.Form):
    data = forms.FileField(label='Quiz JSON Export', help_text='An export file from another quiz that you would like to duplicate here.')

    def __init__(self, quiz: Quiz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiz = quiz

    def clean_data(self):
        """
        Actually handle the JSON input; normalizes data to a triple (Quiz, [Question], [Version]), all of which are
        *unsaved*.
        """
        byte_data = self.cleaned_data['data'].read()
        try:
            str_data = byte_data.decode('utf-8')
        except UnicodeDecodeError:
            raise forms.ValidationError('Bad UTF-8 data')

        try:
            data = json.loads(str_data)
        except json.JSONDecodeError:
            raise forms.ValidationError('Bad JSON data')

        quiz = self.quiz
        try:
            if not isinstance(data['config'], dict):
                raise forms.ValidationError('Data["config"] must be a dict')
            config = {k: v for k, v in data['config'].items() if k in Quiz.ALLOWED_IMPORT_CONFIG}

            if 'grace' in config and not isinstance(config['grace'], int):
                raise forms.ValidationError('Data["config"]["grace"] must be an integer')

            quiz.config.update(config)
        except KeyError:
            pass

        try:
            intro = data['intro']
            if not (
                isinstance(intro, list) and len(intro) == 3
                and isinstance(intro[0], str)
                and isinstance(intro[1], str) and intro[1] in MARKUPS
                and isinstance(intro[2], bool)
            ):
                raise forms.ValidationError('Data["intro"] must be a triple of (text, markup_language, math_bool).')
            quiz.config['intro'], quiz.config['markup'], quiz.config['math'] = data['intro']
        except KeyError:
            pass

        try:
            questions = data['questions']
            if not isinstance(questions, list):
                raise forms.ValidationError('Data["questions"] must be a list of questions.')
        except KeyError:
            raise forms.ValidationError('Missing "questions" section in data')

        new_questions = []
        new_versions = []
        for i, q in enumerate(questions):
            qlabel = 'Data["questions"][%i]' % (i,)
            try:
                points = decimal.Decimal(q['points'])
            except KeyError:
                raise forms.ValidationError(qlabel + '["points"] missing.')
            except decimal.InvalidOperation:
                raise forms.ValidationError(qlabel + '["points"] must be an integer (or decimal represented as a string).')

            try:
                qtype = q['type']
                if not (isinstance(qtype, str) and qtype in QUESTION_HELPER_CLASSES):
                    raise forms.ValidationError(qlabel + '["type"] must be a valid question type.')
            except KeyError:
                raise forms.ValidationError(qlabel + '["type"] missing.')

            question = Question(quiz=quiz, type=qtype)
            question.points = points
            question.order = i+1
            new_questions.append(question)

            try:
                versions = q['versions']
                if not (isinstance(versions, list) and len(versions) >= 1):
                    raise forms.ValidationError(qlabel + '["versions"] must be a list of question versions.')
            except KeyError:
                raise forms.ValidationError(qlabel + '["versions"] missing.')

            for j, v in enumerate(versions):
                vlabel = qlabel + '["versions"][%i]' % (j,)
                if not isinstance(v, dict):
                    raise forms.ValidationError(vlabel + ' must be a dict')
                version = QuestionVersion(question=question)
                helper = version.helper(question=question)
                try:
                    version.config = helper.process_import(v, points)
                except forms.ValidationError as e:
                    # make the error message a little prettier
                    raise forms.ValidationError(vlabel + e.message)
                new_versions.append(version)

        return quiz, new_questions, new_versions


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
