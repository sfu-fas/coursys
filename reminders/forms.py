from .models import Reminder
from django import forms
from coredata.models import Unit, Course, CourseOffering, Member

from courselib.markup import MarkupContentMixin, MarkupContentField
import datetime


class RoleUnitWidget(forms.MultiWidget):
    def __init__(self, *args, **kwargs):
        widgets = [
            forms.TextInput(),
            forms.TextInput()
        ]
        super().__init__(widgets=widgets, *args, **kwargs)
    def decompress(self, value):
        if value:
            return value.split(' ')
        return [None, None]


class RoleUnitField(forms.MultiValueField):
    widget = RoleUnitWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.CharField(),
            forms.CharField()
        )
        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        return ' '.join(data_list)


class ReminderForm(MarkupContentMixin(), forms.ModelForm):
    content = MarkupContentField()
    #role_unit = RoleUnitField()

    def __init__(self, person, *args, **kwargs):
        courses_set = Reminder.relevant_courses(person)
        courses = sorted(list(courses_set))
        course_choices = [(c.id, str(c)) for c in courses]

        super().__init__(*args, **kwargs)
        self.fields['course'].choices = [(None, '\u2014')] + course_choices
        # don't show nulls, or INST if user isn't an instructor of anything
        self.fields['reminder_type'].choices = [(k,v) for k,v in self.fields['reminder_type'].choices if k
                                                and (courses_set or k != 'INST')]
        self.fields['date_type'].choices = [(k,v) for k,v in self.fields['date_type'].choices if k]

    class Meta:
        model = Reminder
        exclude = ['person', 'config', 'status']
        widgets = {
            'reminder_type': forms.RadioSelect,
            'date_type': forms.RadioSelect,
        }
