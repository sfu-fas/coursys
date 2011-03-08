from django import forms
from planning.models import *
import re

section_re = re.compile("^[A-Z]\d\d\d$")
LAB_SECTION_CHOICES = (
    ('0', '0'),
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
)

class ModelFormWithInstructor(forms.ModelForm):
    def clean(self):
        if self.instructor_id != self.cleaned_data['instructor'].id:
            raise forms.ValidationError("Incorrect instructor.")

        return super(ModelFormWithInstructor, self).clean()

class CapabilityForm(ModelFormWithInstructor):
    class Meta:
        model = TeachingCapability
        widgets = {
            'instructor': forms.HiddenInput(),
            'note': forms.Textarea(attrs={'rows':2, 'cols':40}),
        }

class IntentionForm(ModelFormWithInstructor):
    class Meta:
        model = TeachingIntention
        exclude = ('intentionfull',)
        widgets = {
            'instructor': forms.HiddenInput(),
            'count': forms.TextInput(attrs={'size':2}),
            'note': forms.Textarea(attrs={'rows':2, 'cols':40}),
        }

class PlanBasicsForm(forms.ModelForm):
    class Meta:
        model = SemesterPlan


class OfferingBasicsForm(forms.ModelForm):

    #lab_sections = forms.CharField()
    lab_sections = forms.ChoiceField(choices=LAB_SECTION_CHOICES) 
    def clean_section(self):
        section = self.cleaned_data['section']
        if not section_re.match(section):
            raise forms.ValidationError("Bad section label")
        return section
        
    class Meta:
        model = PlannedOffering
        fields = ('course','section','component','campus','enrl_cap')

class OfferingInstructorForm(forms.ModelForm):
    class Meta:
        model = PlannedOffering
        fields = ('instructor',)

