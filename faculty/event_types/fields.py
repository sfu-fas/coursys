from django import forms
from django.utils.encoding import smart_str
from fractions import Fraction
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
import copy
import datetime

from coredata.models import Semester
from coredata.models import SemesterWeek


class SemesterDateInput(forms.widgets.MultiWidget):
   
    def __init__(self, attrs=None, mode=0):
        _widgets = (
            forms.widgets.DateInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
        )
        super(SemesterDateInput, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            return [value, None]
        return [None, None]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

    def value_from_datadict(self, data, files, name):
        datelist = [w.value_from_datadict(data, files, "%s_%s" %(name, i)) for i, w, in enumerate(self.widgets)]
        semester = None
        first = None
        date = None
        try:
            y, m, d = datelist[0].split('-')
            date = datetime.date(int(y), int(m), int(d))
        except ValueError:
            pass

        # Date field is blank, try to get the semester
        semester = datelist[1]
        try:
            assert len(semester) == 4
            assert semester.isdigit()
            s = Semester.objects.get(name=semester)
            weeks = SemesterWeek.objects.filter(semester=s)
            first = weeks[0].monday
        except (AssertionError, Semester.DoesNotExist, IndexError):
            # Semester does not exist, or is in wrong format
            pass

        # TODO: Precedence to semester if they're both filled in?
        if date and first:
            return first 
        elif first:
            return first
        elif date:
            return date
        else:
            return ""

class SemesterField(forms.DateField):
    widget = SemesterDateInput

    def __init__(self, **kwargs):
        defaults = kwargs
        defaults.update({"help_text": mark_safe('Select Date or enter semester code on the right, e.g.: 1141')})
        super(SemesterField, self).__init__(**defaults)

    def to_python(self, value):
        if value in forms.fields.validators.EMPTY_VALUES:
            return None
        else:
            return value
    

class DollarInput(forms.widgets.NumberInput):
    "A NumberInput, but with a prefix '$'"
    def __init__(self, **kwargs):
        defaults = {'attrs': {'size': 8}}
        defaults.update(**kwargs)
        super(DollarInput, self).__init__(**defaults)

    def render(self, *args, **kwargs):
        return '$ ' + super(DollarInput, self).render(*args, **kwargs)


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
