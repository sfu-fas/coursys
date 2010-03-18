from django import forms
from django.conf import settings
from grades.models import ACTIVITY_STATUS_CHOICES, NumericActivity, Activity
from django.utils.safestring import mark_safe

_required_star = '<span><img src="'+settings.MEDIA_URL+'icons/required_star.gif" alt="required"/></span>'

FORMTYPE = {'add': 'add', 'edit': 'edit'}

class NumericActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label=mark_safe('Name:'+_required_star), help_text='e.g. "Assignment 1" or "Midterm"',
            widget=forms.TextInput(attrs={'size':'30'}))
    short_name = forms.CharField(max_length=15, label=mark_safe('Short name:' + _required_star), help_text='short version of the name for column headings, e.g. "A1" or "MT"',
            widget=forms.TextInput(attrs={'size':'8'}))
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label=mark_safe('Status:' + _required_star), help_text='visibility of grades/activity to students')
    due_date = forms.DateTimeField(label=mark_safe('Due date:'), required=False)
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage:', help_text='percent of final mark',
            widget=forms.TextInput(attrs={'size':'2'}))
    max_grade = forms.DecimalField(max_digits=5, decimal_places=2, label=mark_safe('Maximum grade:' + _required_star), help_text='maximum grade for the activity',
            widget=forms.TextInput(attrs={'size':'3'}))
    #specify_numeric_formula = forms.BooleanField(label='Specify formula:', required=False)
    
    def __init__(self, *args, **kwargs):
        super(NumericActivityForm, self).__init__(*args, **kwargs)
        self.addform_validate = False
        self.editform_validate = False
    
    def activate_addform_validation(self, course_slug):
        self.addform_validate = True
        self.course_slug = course_slug
        
    def activate_editform_validation(self, course_slug, activity_slug):
        self.editform_validate = True
        self.course_slug = course_slug
        self.activity_slug = activity_slug

    def clean_name(self):
        name = self.cleaned_data['name']
        if name:
            if self.addform_validate:
                if Activity.objects.filter(offering__slug=self.course_slug, name=name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
            elif self.editform_validate:
                if Activity.objects.exclude(slug=self.activity_slug).filter(offering__slug=self.course_slug, name=name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
        return name
    
    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if short_name:
            if self.addform_validate:
                if Activity.objects.filter(offering__slug=self.course_slug, short_name=short_name):
                    raise forms.ValidationError(u'Activity with the same short name has already existed')
            elif self.editform_validate:
                if Activity.objects.exclude(slug=self.activity_slug).filter(offering__slug=self.course_slug, short_name=short_name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
        return short_name
    
    
class LetterActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label=mark_safe('Name:'+_required_star), help_text='e.g. "Assignment 1" or "Midterm"',
            widget=forms.TextInput(attrs={'size':'30'}))
    short_name = forms.CharField(max_length=15, label=mark_safe('Short name:' + _required_star), help_text='short version of the name for column headings, e.g. "A1" or "MT"',
            widget=forms.TextInput(attrs={'size':'8'}))
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label=mark_safe('Status:' + _required_star), help_text='visibility of grades/activity to students')
    due_date = forms.DateTimeField(label=mark_safe('Due date:'), required=False)
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage:', help_text='percent of final mark',
            widget=forms.TextInput(attrs={'size':'2'}))
    #specify_letter_formula = forms.BooleanField(label='Specify formula:', required=False)
    
    def __init__(self, *args, **kwargs):
        super(LetterActivityForm, self).__init__(*args, **kwargs)
        self.addform_validate = False
        self.editform_validate = False
        
    def activate_addform_validation(self, course_slug):
        self.addform_validate = True
        self.course_slug = course_slug
        
    def activate_editform_validation(self, course_slug, activity_slug):
        self.editform_validate = True
        self.course_slug = course_slug
        self.activity_slug = activity_slug
        
    def clean_name(self):
        name = self.cleaned_data['name']
        if name:
            if self.addform_validate:
                if Activity.objects.filter(offering__slug=self.course_slug, name=name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
            elif self.editform_validate:
                if Activity.objects.exclude(slug=self.activity_slug).filter(offering__slug=self.course_slug, name=name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
        return name
    
    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if short_name:
            if self.addform_validate:
                if Activity.objects.filter(offering__slug=self.course_slug, short_name=short_name):
                    raise forms.ValidationError(u'Activity with the same short name has already existed')
            elif self.editform_validate:
                if Activity.objects.exclude(slug=self.activity_slug).filter(offering__slug=self.course_slug, short_name=short_name):
                    raise forms.ValidationError(u'Activity with the same name has already existed')
        return short_name


class _MyModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name
    
#Todo: Not yet complete, to be combined with LetterActivityForm
class CalLetterActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label='Name:')
    short_name = forms.CharField(max_length=15, label='Short name:')
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS', label='Status:')
    due_date = forms.DateTimeField(required=False, label='Due date:')
    numeric_activity = _MyModelChoiceField(queryset=NumericActivity.objects.none(), empty_label=None)
    
    def __init__(self, course_slug, *args, **kwargs):
        super(CalLetterActivityForm, self).__init__(*args, **kwargs)
        self.fields['numeric_activity'].queryset = NumericActivity.objects.filter(offering__slug=course_slug)
    

