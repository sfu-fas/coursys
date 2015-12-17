# Django
from django import forms
from django.core.exceptions import ValidationError
# App
from coredata.models import Person, CourseOffering
 

class AutocompletePersonWidget(forms.TextInput):
    """
    A widget to allow searching for a person by name or emplid.
    """
    def render(self, name, value, attrs=None):
        if not attrs:
            attrs={'class':'autocomplete_person'}
        elif not 'class' in attrs:
            attrs['class'] = 'autocomplete_person'
        else:
            attrs['class'] = attrs['class'] + " autocomplete_person"
        html = super(AutocompletePersonWidget, self).render(name, value, attrs)
        # This javascript moved to core.js instead
        # html += "<script type='application/javascript'>"
        # html += "$('.autocomplete_person').each(function(){"
        # html += "  $(this).autocomplete({"
        # html += "    source: '/data/students',"
        # html += "    minLength: 2,"
        # html += "    select: function(event, ui){"
        # html += "      $(this).data('val', ui.item.value);"
        # html += "    }"
        # html += "  });"
        # html += "});"
        # html += "</script>"
        return html

class PersonField(forms.CharField):
    """
    A field to allow emplid entry of a Person, with autocomplete,
    but no SIMS integration.
    """
    def __init__(self, *args, **kwargs):
        widget = AutocompletePersonWidget()
        kwargs['widget'] = widget
        if 'initial' in kwargs:
            kwargs['initial'] = Person.objects.get(id=kwargs['initial']).emplid
        return super(PersonField, self).__init__(*args, **kwargs)

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

    def render(self, name, value, attrs=None):
        if not attrs:
            attrs={'class':'autocomplete_courseoffering'}
        elif not 'class' in attrs:
            attrs['class'] = 'autocomplete_courseoffering'
        else:
            attrs['class'] = attrs['class'] + " autocomplete_courseoffering"
        

        html = super(AutocompleteOfferingWidget, self).render(name, value, attrs)
        html += "<script type='application/javascript'>"
        html += "$('.autocomplete_courseoffering').each(function(){"
        html += "  $(this).autocomplete({"
        try:
            html += "    source: '/data/offerings_slug/"+self.semester+"',"
        except AttributeError:
            html += "    source: '/data/offerings_slug',"
        html += "    minLength: 2,"
        html += "    select: function(event, ui){"
        html += "      $(this).data('val', ui.item.value);"
        html += "    }"
        html += "  });"
        html += "});"
        html += "</script>"
        return html

class OfferingField(forms.CharField):
    def __init__(self, *args, **kwargs):
        widget = AutocompleteOfferingWidget()
        kwargs['widget'] = widget
        return super(OfferingField, self).__init__(*args, **kwargs)
    
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
    def render(self, name, value, attrs=None):
        if not attrs:
            attrs={'class':'datepicker'}
        elif not 'class' in attrs:
            attrs['class'] = 'datepicker'
        else:
            attrs['class'] = attrs['class'] + " datepicker"
        html = super(CalendarWidget, self).render(name, value, attrs)
        # The Javascript should be done in core.js instead.
        # html += "<script type='application/javascript'>"
        # html += "$('.datepicker').each(function(){"
        # html += "  $(this).datepicker({'dateFormat': $.datepicker.ISO_8601}); "
        # html += "});"
        # html += "</script>"
        return html
