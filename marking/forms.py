from models import *
from django.forms import ModelForm
from django import forms
from django.forms.models import BaseModelFormSet

class ActivityComponentMarkForm(ModelForm):
    
    class Meta:
        model = ActivityComponentMark            
        fields = ['comment', 'value']
    
           
class ActivityMarkForm(ModelForm):
    class Meta:
        model = ActivityMark
        fields = ['late_penalty', 'mark_adjustment', 'mark_adjustment_reason', 'overall_comment', \
                  'file_attachment']
    
    def clean_late_penalty(self):  
        late_penalty = self.cleaned_data['late_penalty']
        if late_penalty:
            if late_penalty < 0:          
                raise forms.ValidationError(u'The late penalty can not be negative')
            elif late_penalty > 100:
                raise forms.ValidationError(u'The late penalty can not exceed 100 percent')
        return late_penalty
    
class BaseActivityComponentFormSet(BaseModelFormSet):
    
    def __init__(self, activity, *args, **kwargs):
        self.activity =  activity
        super(BaseActivityComponentFormSet, self).__init__(*args, **kwargs)
        
    def clean(self):
        """Checks the following:
        1. no two component have the same title  
        2. max mark of each component is non-negative 
        """
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
             return
        # check titles
        titles = []
        for form in self.forms:
            try: # since title is required, empty title triggers KeyError and don't consider this row
                form.cleaned_data['title']
            except KeyError:      
                continue
            else:  
                title = form.cleaned_data['title']
                if (not form.cleaned_data['deleted']) and title in titles:
                    raise forms.ValidationError(u"Each component must have an unique title")
                titles.append(title)  
        
        # check max marks
        for form in self.forms:
            try:
                form.cleaned_data['title']
            except KeyError:
                continue                        
            max_mark = form.cleaned_data['max_mark']
            if max_mark < 0:
                raise forms.ValidationError(u"Max mark of a component can not be negative")
            
            
class BaseCommonProblemFormSet(BaseModelFormSet):
    
    def __init__(self, activity_components, *args, **kwargs):
        super(BaseCommonProblemFormSet, self).__init__(*args, **kwargs)
        if activity_components:
            for form in self.forms:
                # limit the choices of activity components
                form.fields['activity_component'].queryset = activity_components
    
    def clean(self):
        """Checks the following:
        1. no two common problems in a same component have the same title  
        2. penalty of each common problem is non-negative
        3. penalty of each common problem does not exceed the max mark of its corresponding component
        """   
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
             return
        # check titles
        common_problems = {}
        for form in self.forms:
            try: # component is required, empty component triggers KeyError and don't consider this row
                component = form.cleaned_data['activity_component']
            except KeyError:
                continue
            
            title = form.cleaned_data['title']
            if (not form.cleaned_data['deleted']) and \
               component in common_problems.keys() and \
               common_problems[component].count(form.cleaned_data['title']) > 0:
               raise forms.ValidationError(u"Each common problem must have an unique title within one component")
           
            if not form.cleaned_data['deleted']:
                if not component in common_problems.keys():
                    common_problems[component] = [];
                common_problems[component].append(title)
                      
        # check penalty       
        for form in self.forms:
            try: 
                component = form.cleaned_data['activity_component']
            except KeyError:
                continue
            
            penalty = form.cleaned_data['penalty']                      
            if penalty:           
                if penalty < 0:
                    raise forms.ValidationError(u"Penalty of a common problem must not be negative")
                if penalty > component.max_mark:
                    raise forms.ValidationError(u"Penalty of a common problem must not exceed its corresponding component")
                          

class MarkEntryForm(forms.Form):
    value = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    
class UploadGradeFileForm(forms.Form):
    file = forms.FileField(required=False)
    
    def clean_file(self):        
        file = self.cleaned_data['file']
        if file != None and (not file.name.endswith('.csv')) and\
           (not file.name.endswith('.CSV')):
            raise forms.ValidationError(u"Only .csv files are permitted")
        return file
            
                          