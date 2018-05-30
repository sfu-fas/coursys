from .models import Reminder
from django import forms
from coredata.models import Unit, Role, ROLES

from courselib.markup import MarkupContentMixin, MarkupContentField
from collections import OrderedDict
import datetime


class ReminderForm(MarkupContentMixin(), forms.ModelForm):
    content = MarkupContentField(allow_math=False, restricted=True)
    role_unit = forms.ChoiceField(label='Role', choices=[], required=False)  # choices filled by __init__

    def __init__(self, person, *args, **kwargs):
        self.person = person
        courses_set = Reminder.relevant_courses(person)
        courses = sorted(list(courses_set))
        course_choices = [(c.id, str(c)) for c in courses]
        role_unit_choices = [
            ('%s %s' % (r.role, r.unit_id), '%s(s) in %s' % (ROLES[r.role], r.unit.label))
            for r in Role.objects_fresh.filter(person=person)
        ]

        super().__init__(*args, **kwargs)

        # set initial for the role_unit field
        if 'role' in self.initial and self.initial['role'] and 'unit' in self.initial and self.initial['unit']:
            self.initial['role_unit'] = '%s %i' % (self.initial['role'], self.initial['unit'])
        else:
            self.initial['role_unit'] = None

        self.fields['course'].choices = [(None, '\u2014')] + course_choices
        # don't show nulls, or INST if user isn't an instructor of anything
        self.fields['reminder_type'].choices = [(k,v) for k,v in self.fields['reminder_type'].choices if k
                                                and (courses_set or k != 'INST')]
        self.fields['date_type'].choices = [(k,v) for k,v in self.fields['date_type'].choices if k]
        self.fields['role_unit'].choices = role_unit_choices

        # reorder fields... painfully.
        role_unit = self.fields['role_unit']
        new_order = OrderedDict()
        for n, f in self.fields.items():
            if n in ['role_unit', 'role', 'unit']:
                continue
            elif n == 'course':
                new_order['role_unit'] = role_unit
            new_order[n] = f

        self.fields = new_order

    class Meta:
        model = Reminder
        exclude = ['person', 'config', 'status']
        widgets = {
            'reminder_type': forms.RadioSelect,
            'date_type': forms.RadioSelect,
        }

    def clean_week(self):
        week = self.cleaned_data['week']
        if week is not None and week < 0:
            raise forms.ValidationError('Week number must be positive.')
        if week is not None and week > 16:
            raise forms.ValidationError('Week number can be no more than 16.')
        return week

    def require_null(self, cleaned_data, fields):
        """
        Make sure the field is null. Should only be an issue if the form is fiddled with: UI hides these fields.
        """
        for f in fields:
            cleaned_data[f] = None

    def require_non_null(self, cleaned_data, fields):
        """
        Make sure these situationally-required fields are non-null.
        """
        for f in fields:
            if f not in cleaned_data or not bool(cleaned_data[f]):
                self.add_error(f, 'This field is required.')

    def clean(self):
        cleaned_data = super().clean()

        # instructor reminders can only be semesterly
        if 'reminder_type' in cleaned_data and cleaned_data['reminder_type'] == 'INST' \
                and 'date_type' in cleaned_data and cleaned_data['date_type'] != 'SEM':
            self.add_error('date_type', 'Course-teaching reminders can only be semesterly.')

        # make sure the right fields are null/non-null for the various reminder_types and date_types
        if 'reminder_type' in cleaned_data:
            if cleaned_data['reminder_type'] == 'PERS':
                self.require_null(cleaned_data, ['role_unit', 'course'])
            elif cleaned_data['reminder_type'] == 'INST':
                self.require_null(cleaned_data, ['role_unit'])
                self.require_non_null(cleaned_data, ['course'])
            elif cleaned_data['reminder_type'] == 'ROLE':
                self.require_null(cleaned_data, ['course'])
                self.require_non_null(cleaned_data, ['role_unit'])
            else:
                raise forms.ValidationError('Unknown reminder type')

        if 'date_type' in cleaned_data:
            if cleaned_data['date_type'] == 'SEM':
                self.require_null(cleaned_data, ['month', 'day'])
                self.require_non_null(cleaned_data, ['week', 'weekday'])
            elif cleaned_data['date_type'] == 'YEAR':
                self.require_null(cleaned_data, ['week', 'weekday'])
                self.require_non_null(cleaned_data, ['month', 'day'])
            else:
                raise forms.ValidationError('Unknown date type')

        if 'role_unit' in cleaned_data and cleaned_data['role_unit'] is not None:
            # fill role and unit from role_unit
            role_unit = cleaned_data['role_unit']
            role_name, unit_id = role_unit.split(' ')
            unit = Unit.objects.get(id=unit_id)
            cleaned_data['unit'] = unit
            cleaned_data['role'] = role_name
        else:
            cleaned_data['unit'] = None
            cleaned_data['role'] = None

        # make sure month/day forms a valid date
        if 'month' in cleaned_data and cleaned_data['month'] is not None \
                and 'day' in cleaned_data and cleaned_data['day'] is not None:
            try:
                # poor Feb 29, never getting the respect it deserves.
                datetime.date(year=2001, month=int(cleaned_data['month']), day=cleaned_data['day'])
            except ValueError:
                self.add_error('day', 'Not a valid day in that month.')

        return cleaned_data
