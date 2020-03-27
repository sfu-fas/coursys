from django import forms

from courselib.markup import MarkupContentField
from grades.models import Activity
from quizzes.models import Quiz


class QuizForm(forms.ModelForm):
    start = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    end = forms.SplitDateTimeField(required=True, help_text='Quiz will be visible after this time. Time format: HH:MM:SS, 24-hour time')
    intro = MarkupContentField(label='Introductory Text (displayed at the top of the quiz)', default_markup='creole', with_wysiwyg=True)

    start.widget.widgets[0].attrs.update({'class': 'datepicker'})
    end.widget.widgets[0].attrs.update({'class': 'datepicker'})

    class Meta:
        model = Quiz
        fields = ['start', 'end']
        widgets = {}

    def __init__(self, activity: Activity, *args, **kwargs):
        self.activity = activity
        super().__init__(*args, **kwargs)
        # fill initial data from .config
        self.initial['intro'] = [self.instance.intro, self.instance.intro_markup, self.instance.intro_math]

    def clean(self):
        cleaned_data = super().clean()
        # all Quiz instances must have the activity where we're editing
        self.instance.activity = self.activity
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # fill .config from cleaned_data
        instance.intro, instance.intro_markup, instance.intro_math = self.cleaned_data['intro']
        if commit:
            instance.save()
        return instance
