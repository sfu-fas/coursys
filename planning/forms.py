from django import forms
from django.forms.widgets import RadioSelect
from planning.models import *
import re

section_re = re.compile("^[A-Z]\d\d\d$")
LAB_SECTION_CHOICES = [(str(i), str(i)) for i in range(20)]


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
        model = PlanningCourse
        exclude = ('config', 'status')
    fields = ('subject', 'number', 'title', 'owner')


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
        fields = ('copy_plan_from','semester', 'name', 'visibility')


class OfferingBasicsForm(forms.ModelForm):
    lab_sections = forms.ChoiceField(choices=LAB_SECTION_CHOICES, label="Additional sections")
    lab_enrl_cap = forms.IntegerField(label="Additional section cap", required=False)
    enrl_cap = forms.IntegerField(label="Enrollment cap")

    def clean_section(self):
        section = self.cleaned_data['section']
        if not section_re.match(section):
            raise forms.ValidationError("Invalid section label")
        return section

    def clean_lab_enrl_cap(self):
        lab_sections = self.cleaned_data['lab_sections']
        lab_enrl_cap = self.cleaned_data['lab_enrl_cap']
        if lab_sections > 0 and not isinstance(lab_enrl_cap, int):
            raise forms.ValidationError("Lab enrollment cap is required when adding lab sections")
        return lab_enrl_cap

    class Meta:
        model = PlannedOffering
        fields = ('course', 'section', 'component', 'campus', 'enrl_cap')


class OfferingInstructorForm(forms.ModelForm):
    class Meta:
        model = PlannedOffering
        fields = ('instructor',)