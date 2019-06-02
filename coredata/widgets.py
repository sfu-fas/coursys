import os
# Django
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html, conditional_escape
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
# App
from coredata.models import Person, CourseOffering, FuturePerson, AnyPerson
 

class PersonField(forms.CharField):
    """
    A field to allow emplid entry of a Person, with autocomplete,
    but no SIMS integration.
    """
    def __init__(self, *args, **kwargs):
        widget = forms.TextInput(attrs={'class': 'autocomplete_person'})
        kwargs['widget'] = widget
        if 'initial' in kwargs:
            kwargs['initial'] = Person.objects.get(id=kwargs['initial']).emplid
        super(PersonField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        if value:
            try:
                return Person.objects.get(id=value).emplid
            except ValueError:
                return value
            except Person.DoesNotExist:
                return value
        else:
            return value

    def clean(self, value):
        if isinstance(value, Person):
            return value
        else:
            if not self.required and not value:
                return None
            try:
                return Person.objects.get(emplid=value)
            except Person.DoesNotExist:
                raise ValidationError("That Person cannot be found.")
            except ValueError:
                raise ValidationError("Please enter a 9-digit EMPLID.")


class AutocompleteOfferingWidget(forms.TextInput):
    """
    A widget to allow searching for a CourseOffering
    """

    def render(self, name, value, attrs=None, renderer=None):
        if not attrs:
            attrs={'class':'autocomplete_courseoffering'}
        elif not 'class' in attrs:
            attrs['class'] = 'autocomplete_courseoffering'
        else:
            attrs['class'] = attrs['class'] + " autocomplete_courseoffering"

        try:
            attrs['data-semester'] = self.semester
        except AttributeError:
            pass

        html = super().render(name, value, attrs=attrs, renderer=renderer)
        return html


class OfferingField(forms.CharField):
    def __init__(self, *args, **kwargs):
        widget = AutocompleteOfferingWidget()
        kwargs['widget'] = widget
        super(OfferingField, self).__init__(*args, **kwargs)
    
    def prepare_value(self, value):
        if value:
            try:
                return CourseOffering.objects.get(id=value).slug
            except ValueError:
                return value
            except CourseOffering.DoesNotExist:
                return value
        else:
            return value
    
    def clean(self, value):
        if isinstance(value, CourseOffering):
            return value
        else:
            if not self.required and not value:
                return None
            try:
                return CourseOffering.objects.get(slug=value)
            except ValueError:
                raise ValidationError("That's not a valid course slug.")
            except CourseOffering.DoesNotExist:
                raise ValidationError("That Course Offering could not be found.")


class CalendarWidget(forms.TextInput):
    """
    A widget for calendar date-pickin' 
    """
    def render(self, name, value, attrs=None, renderer=None):
        if not attrs:
            attrs={'class':'datepicker'}
        elif not 'class' in attrs:
            attrs['class'] = 'datepicker'
        else:
            attrs['class'] = attrs['class'] + " datepicker"
        html = super(CalendarWidget, self).render(name, value, attrs=attrs, renderer=renderer)
        return html


class NotClearableFileInput(forms.FileInput):
    """
    Every once in a while, we want a file input without the "clear" checkbox of the default ClearableFileInput,
    but with the capability to display the currently selected instance value, like the ClearableFileInput (the
    plain FileInput we are subclassing here has no such capability).

    This is useful in the case of required fields where we want to display the current value but not allow clearing
    of it, but only submission of a new one.

    We also don't want to give a full link to the original file like ClearableFileInput, as we most likely don't
    have a view for that, and why trigger an exception?  We just want to show the filename of what the user has
    already uploaded.

    Modified from:
    http://stackoverflow.com/questions/17293627/hide-django-clearablefileinput-checkbox
    """
    initial_text = 'Currently'
    input_text = 'Change'

    template_with_initial = '%(initial_text)s: %(initial)s <br />%(input_text)s: %(input)s'

    def render(self, name, value, attrs=None, renderer=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
        }
        template = '%(input)s'
        substitutions['input'] = super(NotClearableFileInput, self).render(name, value, attrs=attrs, renderer=renderer)

        if value:
            template = self.template_with_initial
            substitutions['initial'] = format_html(force_text(os.path.basename(value.name)))

        return mark_safe(template % substitutions)


class DollarInput(forms.NumberInput):
    template_name = 'coredata/dollar_input.html'
    "A NumberInput, but with a prefix '$'"
    def __init__(self, **kwargs):
        defaults = {'attrs': {'size': 8}}
        defaults.update(**kwargs)
        super(DollarInput, self).__init__(**defaults)
