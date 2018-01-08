from django import forms
from .models import TeachingEquivalent
from django.forms.widgets import TextInput, Textarea
from django.core import validators
from django.core.exceptions import ValidationError
from fractions import Fraction


class TeachingCreditField(forms.Field):
    
    def to_python(self, value):
        
        if value in validators.EMPTY_VALUES and self.required:
            raise ValidationError(self.error_messages['required'])
        if '.' in value:
            raise ValidationError('Invalid format. Must be a whole number or a proper fraction')
        
        try:
            value = Fraction(value)
        except ValueError:
            raise ValidationError('Invalid format. Must be a whole number or a proper fraction')
        except ZeroDivisionError:
            raise ValidationError('Denominator of fraction cannot be zero')
        
        return value

class TeachingEquivForm(forms.ModelForm):
    credits = TeachingCreditField(help_text='The number of credits this equivalent is worth')
    class Meta:
        model = TeachingEquivalent
        exclude = ('status', 'instructor', 'credits_numerator', 'credits_denominator')
        widgets = {
                   'summary': TextInput(attrs={'size': 60}),
                   'comment': Textarea(attrs={'cols': 60, 'rows': 15}),
                   }
        
    def __init__(self, *args, **kwargs):
        super(TeachingEquivForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['semester', 'summary', 'credits', 'comment']
    
    def clean(self):
        cleaned_data = self.cleaned_data
        credits_value = cleaned_data.get('credits')
        if credits_value:
            cleaned_data['credits_numerator'] = credits_value.numerator
            cleaned_data['credits_denominator'] = credits_value.denominator
            del cleaned_data['credits']
        return cleaned_data
    
class CourseOfferingCreditForm(forms.Form):
    credits = TeachingCreditField()