import copy
import datetime

from django import forms
from django.utils.encoding import smart_str
from fractions import Fraction
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.html import conditional_escape

from faculty.util import ReportingSemester


class SemesterDateInput(forms.widgets.MultiWidget):
    class Media:
        js = ('js/semesters.js',)

    def __init__(self, attrs=None, mode=0, semester_start=True):
        self.semester_start = semester_start
        semester_attrs = attrs or {}
        semester_attrs.update({"maxlength": 4, "size": 6, "class": "semester-input"})
        if self.semester_start:
            semester_attrs.update({"class": "semester-input semester-start"})
        date_attrs = {"class": "date-input"}
        _widgets = (
            forms.widgets.DateInput(attrs=date_attrs),
            forms.widgets.TextInput(attrs=semester_attrs),
        )
        super(SemesterDateInput, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            return [value, None]
        return [None, None]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def get_semester(self, code):
        try:
            assert len(code) == 4
            assert code.isdigit()
            #s = Semester.objects.get(name=code)
            s = ReportingSemester(code)
            return s
        except AssertionError:
        #except (AssertionError, Semester.DoesNotExist):
            # Semester does not exist, or its in the wrong format
            return 

    def get_semester_date(self, semester):
        if not semester:
            return 
        start, end = semester.start_and_end_dates(semester.code)
        if self.semester_start:
            return start
        return end

    def value_from_datadict(self, data, files, name):
        datelist = [w.value_from_datadict(data, files, "%s_%s" %(name, i)) for i, w, in enumerate(self.widgets)]
        semester_date = None
        regular_date = None
        try:
            y, m, d = datelist[0].split('-')
            regular_date = datetime.date(int(y), int(m), int(d))
        except ValueError:
            pass

        # Date field is blank, try to get the semester
        code = datelist[1]
        if code:
            semester = self.get_semester(code)
            semester_date = self.get_semester_date(semester)

        # TODO: Precedence to semester if they're both filled in?
        if regular_date and semester_date:
            return regular_date
        elif semester_date:
            return semester_date
        elif regular_date:
            return regular_date
        else:
            return ""

class SemesterField(forms.DateField):
    widget = SemesterDateInput

    def __init__(self, **kwargs):
        start = kwargs.get("semester_start", True)
        kwargs.update({"semester_start": start})
        del kwargs["semester_start"]
        self.semester_start = start
        self.widget = SemesterDateInput(semester_start=start)

        defaults = kwargs
        defaults.update({"help_text": mark_safe('Select Date or enter semester code on the right, e.g.: 1141')})
        super(SemesterField, self).__init__(**defaults)

    def to_python(self, value):
        if value in forms.fields.validators.EMPTY_VALUES:
            return None
        else:
            return value


class SemesterToDateField(forms.CharField):
    """
    A field that represents itself as a semester code input but returns a date.
    """

    def __init__(self, start=True, **kwargs):
        defaults = {
            'help_text': mark_safe('Enter semester code, e.g.: 1141'),
            'label': '{} Semester'.format(start and 'Starting' or 'Ending'),
            'widget': forms.TextInput(attrs={'size': 4}),
        }
        defaults.update(kwargs)
        super(SemesterToDateField, self).__init__(min_length=4, max_length=4, **defaults)
        self.start = start

    def to_python(self, value):
        if value in forms.fields.validators.EMPTY_VALUES:
            return None

        if not (len(value) == 4 and value.isdigit()):
            raise ValidationError(_('Invalid semester code'))

        try:
            semester = ReportingSemester(value)
        except ValueError:
            raise ValidationError(_('Invalid semester code'))

        return self.start and semester.start_date or semester.end_date

    def run_validators(self, value):
        # XXX: Validation is already done inside `to_python`.
        pass

    def prepare_value(self, value):
        if isinstance(value, (unicode, str)):
            return value
        elif value is None:
            return ''
        else:
            return ReportingSemester(value).code


class SemesterCodeField(forms.CharField):
    """
    A field that represents itself as a semester code.
    """

    def __init__(self, **kwargs):
        defaults = {
            'help_text': mark_safe('Enter semester code, e.g.: 1141'),
            'widget': forms.TextInput(attrs={'size': 4}),
        }
        defaults.update(kwargs)
        super(SemesterCodeField, self).__init__(min_length=4, max_length=4, **defaults)

    def to_python(self, value):
        if value in forms.fields.validators.EMPTY_VALUES:
            return None

        if not (len(value) == 4 and value.isdigit() and (value[3] == '1' or value[3] == '4' or value[3] == '7')):
            # XXX: Technically this check isn't needed as the db query would also fail
            #      but maybe we gain something by not making that call?
            raise ValidationError(_('Invalid semester code'))

        return value


class DollarInput(forms.widgets.NumberInput):
    "A NumberInput, but with a prefix '$'"
    def __init__(self, **kwargs):
        defaults = {'attrs': {'size': 8}}
        defaults.update(**kwargs)
        super(DollarInput, self).__init__(**defaults)

    def render(self, *args, **kwargs):
        return mark_safe('$ ' + conditional_escape(super(DollarInput, self).render(*args, **kwargs)))


PAY_FIELD_DEFAULTS = {
    'max_digits': 8,
    'decimal_places': 2,
    'initial': 0,
    'widget': DollarInput,
}

class AddSalaryField(forms.DecimalField):
    def __init__(self, **kwargs):
        defaults = copy.copy(PAY_FIELD_DEFAULTS)
        defaults['help_text'] = mark_safe('Additional salary associated with this event (salary <strong>is adjusted</strong> during leaves)')
        defaults.update(kwargs)
        super(AddSalaryField, self).__init__(**defaults)

class AddPayField(forms.DecimalField):
    def __init__(self, **kwargs):
        defaults = copy.copy(PAY_FIELD_DEFAULTS)
        defaults['help_text'] = mark_safe('Add-pay associated with this event (add-pay <strong>is not adjusted</strong> during leaves)')
        defaults.update(kwargs)
        super(AddPayField, self).__init__(**defaults)


class FractionField(forms.Field):
    # adapted from forms.fields.DecimalField
    default_error_messages = {
        'invalid': _(u'Enter a number.'),
        'max_value': _(u'Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _(u'Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, max_value=None, min_value=None, *args, **kwargs):
        self.max_value, self.min_value = max_value, min_value
        forms.Field.__init__(self, *args, **kwargs)

        if max_value is not None:
            self.validators.append(forms.validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(forms.validators.MinValueValidator(min_value))

    def to_python(self, value):
        """
        Validates that the input is a fraction number. Returns a Fraction
        instance. Returns None for empty values.
        """
        if value in forms.fields.validators.EMPTY_VALUES:
            return None
        value = smart_str(value).strip()
        try:
            value = Fraction(value).limit_denominator(50)
        except ValueError:
            raise forms.fields.ValidationError(self.error_messages['invalid'])
        return value

    def validate(self, value):
        super(FractionField, self).validate(value)
        if value in forms.fields.validators.EMPTY_VALUES:
            return
        return value


class TeachingCreditField(FractionField):
    def __init__(self, **kwargs):
        defaults = {
            'initial': 0,
            'widget': forms.TextInput(attrs={'size': 6}),
            'help_text': mark_safe('Teaching credit <strong>per semester</strong> associated with this event. May be a fraction like &ldquo;1/3&rdquo;.'),
        }
        defaults.update(kwargs)
        super(TeachingCreditField, self).__init__(**defaults)


class TeachingReductionField(FractionField):
    def __init__(self, **kwargs):
        defaults = {
            'initial': 0,
            'widget': forms.TextInput(attrs={'size': 6}),
            'help_text': mark_safe('<strong>Per semester</strong> decrease in teaching load associated with this event. May be a fraction like &ldquo;1/3&rdquo;.'),
        }
        defaults.update(kwargs)
        super(TeachingReductionField, self).__init__(**defaults)
