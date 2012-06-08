from django import forms
from django.forms.widgets import RadioSelect
from planning.models import *
import re

section_re = re.compile("^[A-Z]\d\d\d$")
LAB_SECTION_CHOICES = [(str(i), str(i)) for i in range(16)]

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

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course

class PlanBasicsForm(forms.ModelForm):
    class Meta:
        model = SemesterPlan

class CopyPlanForm(forms.ModelForm):
    copy_plan_from = forms.ChoiceField()
    def __init__(self, *args, **kwargs):
	super(CopyPlanForm, self).__init__(*args, **kwargs)
        self.fields['copy_plan_from'] = forms.ChoiceField(choices=[(o.name, o.name) for o in SemesterPlan.objects.all()])
    
    class Meta:
        model = SemesterPlan
	fields = ('copy_plan_from','semester', 'name', 'visibility', 'active')


class OfferingBasicsForm(forms.ModelForm):
    lab_sections = forms.ChoiceField(choices=LAB_SECTION_CHOICES)
    enrl_cap = forms.IntegerField(label="Enrollment cap")
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


	
	
	
	
	
	
	
	

