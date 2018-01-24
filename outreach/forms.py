from .models import OutreachEvent, OutreachEventRegistration
from django import forms
from coredata.models import Unit
from coredata.widgets import DollarInput, CalendarWidget


class OutreachEventForm(forms.ModelForm):
    extra_questions = forms.CharField(required=False, help_text='Extra questions to ask registrants: one per line',
                                      widget=forms.Textarea())

    def __init__(self, request, *args, **kwargs):
        super(OutreachEventForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None
        self.initial['extra_questions'] = '\n'.join(self.instance.extra_questions)

    class Meta:
        exclude = ['config']
        model = OutreachEvent
        field_classes = {
            'start_date': forms.SplitDateTimeField,
            'end_date': forms.SplitDateTimeField,
        }
        widgets = {
            'description': forms.Textarea,
            'resources': forms.Textarea,
            'location': forms.Textarea,
            'notes': forms.Textarea,
            'cost': DollarInput,
            'score': forms.NumberInput(attrs={'class': 'smallnumberinput'}),
            'start_date': forms.SplitDateTimeWidget,
            'end_date': forms.SplitDateTimeWidget,
        }

    def clean(self):
        cleaned_data = super(OutreachEventForm, self).clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if end_date is not None and end_date < start_date:
            raise forms.ValidationError({'end_date': "End date cannot be before start date.",
                                         'start_date': "End date cannot be before start date."})

    def clean_extra_questions(self):
        extra_questions = self.cleaned_data['extra_questions']
        extra_questions = [q.strip() for q in extra_questions.split('\n') if
                           len(q.strip()) > 0]
        self.instance.extra_questions = extra_questions
        return extra_questions


class OutreachEventRegistrationForm(forms.ModelForm):
    confirm_email = forms.EmailField(required=True)

    class Meta:
        exclude = ['event']
        model = OutreachEventRegistration
        widgets = {
            'notes': forms.Textarea,
            'contact': forms.Textarea,
            'birthdate': CalendarWidget,
        }
        fields = ['last_name', 'first_name', 'middle_name', 'birthdate', 'parent_name', 'parent_phone', 'email',
                  'confirm_email', 'photo_waiver', 'participation_waiver', 'previously_attended', 'school', 'grade',
                  'notes']

    def clean(self):
        cleaned_data = super(OutreachEventRegistrationForm, self).clean()
        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")
        if email != confirm_email:
            raise forms.ValidationError({'confirm_email': "The emails do not match.",
                                         'email': "The emails do not match."})
        if not cleaned_data.get("participation_waiver"):
            raise forms.ValidationError({'participation_waiver': "This waiver must be accepted in order to participate "
                                                                 "in this event."})

    def add_extra_questions(self, event):
        if 'extra_questions' in event.config and len(event.config['extra_questions']) > 0:
            for question in event.config['extra_questions']:
                if 'extra_questions' in self.instance.config and question in self.instance.config['extra_questions']:
                    self.fields[question] = \
                        forms.CharField(label=question,widget=forms.Textarea,
                                        initial=self.instance.config['extra_questions'][question])
                else:
                    self.fields[question] = forms.CharField(label=question, widget=forms.Textarea)
