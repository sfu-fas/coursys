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


class AnnualOrBiweeklySalary(forms.widgets.MultiWidget):
    """
    A widget to return the annual salary if inputed, or to calculate it
    based on the biweekly salary otherwise.

    Magic number: 26.089285714  Here's how we got it:

    There are 365 days in a year, 366 in a leap year.  Thus, 365.25 days on average.
    Thus, we have 52 weeks + 1.25 days on average per year.
    Therefore, number of biweekly periods in a year, on average:
    (52 + 1.25/7) / 2 = 26.089285714
    """


    class Media:
        # To calculate the annual salary on the fly from the biweekly and populate the annual field
        js = ('js/salary.js',)

    def __init__(self, attrs=None):
        annual_attrs = attrs or {}
        biweekly_attrs = attrs or {}
        annual_attrs.update({"size": "8", "step": "0.01", "class": "annual-input", "title": "Annual Salary"})
        biweekly_attrs.update({"size": "7", "step": "0.01", "class": "biweekly-input", "title": "Biweekly Salary"})
        _widgets = (
            forms.widgets.NumberInput(attrs=annual_attrs),
            forms.widgets.NumberInput(attrs=biweekly_attrs)
        )
        super(AnnualOrBiweeklySalary, self).__init__(_widgets, attrs)

    def decompress(self, value):
        # Really, we only care about the one value.  We have to allow 0, however, since that is our initial default
        if value or value == 0:
            return [value, None]
        return [None, None]

    def format_output(self, rendered_widgets):
        # Add our help text right in the rendering so we don't have to add it to every field or do some other magic.
        return mark_safe('$ ' + ' '.join(rendered_widgets) + '<br/>' +
                         "<span class=helptext>Enter annual salary on the left <strong>or</strong> biweekly salary "
                         "on the right.</span>")

    def value_from_datadict(self, data, files, name):
        salarylist = [w.value_from_datadict(data, files, "%s_%s" % (name, i)) for i, w, in enumerate(self.widgets)]
        annualsalary = salarylist[0]
        biweeklysalary = salarylist[1]
        if annualsalary:
            return annualsalary
        elif biweeklysalary:
            # Only reachable if someone puts in the biweekly salary and Javascript is off or they delete the value
            # in the annual salary.  Fairly unlikely, so we can do the same calculation the JS would.
            return round(float(biweeklysalary) * 26.089285714, 2)
        else:
            return None


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
        return ' '.join(rendered_widgets)

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
        if 'help_text' in kwargs:
            defaults.update({"help_text": kwargs['help_text']})
        else:
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
        if isinstance(value, str):
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
    'widget': AnnualOrBiweeklySalary,
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
        'invalid': _('Enter a number.'),
        'max_value': _('Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _('Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, max_value=None, min_value=None, choices=None, *args, **kwargs):
        self.max_value, self.min_value = max_value, min_value
        if choices:
            forms.Field.__init__(self, widget=forms.widgets.RadioSelect(choices=choices), *args, **kwargs)
        else:
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

class SemesterTeachingInput(forms.widgets.TextInput):
    def render(self, *args, **kwargs):
        return mark_safe(conditional_escape(super(SemesterTeachingInput, self).render(*args, **kwargs)) + " courses per <strong>semester</strong>")


class TeachingCreditField(FractionField):
    def __init__(self, **kwargs):
        defaults = {
            'initial': 0,
            'widget': SemesterTeachingInput(attrs={'size': 5}),
            'help_text': mark_safe('Teaching credit per semester associated with this event. May be a fraction like &ldquo;1/3&rdquo;.'),
        }
        defaults.update(kwargs)
        super(TeachingCreditField, self).__init__(**defaults)



class TeachingReductionField(FractionField):
    def __init__(self, **kwargs):
        defaults = {
            'initial': 0,
            'widget': SemesterTeachingInput(attrs={'size': 5}),
            'help_text': mark_safe('Per semester decrease in teaching load associated with this event. May be a fraction like &ldquo;1/3&rdquo;.'),
        }
        defaults.update(kwargs)
        super(TeachingReductionField, self).__init__(**defaults)




# Annual field to allow entering per-year teaching credits while storing per-semester values.
# Adapted from https://djangosnippets.org/snippets/1914/

class AnnualTeachingInput(forms.widgets.TextInput):
    def _format_value(self, value):
        if value is None:
            return ''
        try:
            f = Fraction(value).limit_denominator(50)
        except ValueError:
            return str(value)

        return str(f*3)

    def render(self, *args, **kwargs):
        return mark_safe(conditional_escape(super(AnnualTeachingInput, self).render(*args, **kwargs)) + " courses per <strong>year</strong>")


class AnnualTeachingCreditField(TeachingCreditField):
    def __init__(self, **kwargs):
        defaults = {
            'widget': AnnualTeachingInput(attrs={'size': 5}),
        }
        defaults.update(kwargs)
        super(AnnualTeachingCreditField, self).__init__(**defaults)

    def clean(self, value):
        v = super(AnnualTeachingCreditField, self).clean(value)
        if not v:
            return v
        return v/3
