from django import forms
from ta.models import *
from coredata.models import Member

class MultiTextInput(forms.widgets.MultiWidget):
    def __init__(self, widget_count, *args, **kwargs):
        super(MultiTextInput, self).__init__((
            forms.widgets.TextInput,)*widget_count, 
            *args, **kwargs)
        self.widget_count = widget_count
#    def format_output(self, rendered_widgets):
#        '''
#        Overridden
#        '''
#        return u'</td><td>'.join(rendered_widgets)
        
    def decompress(self, value):
        if value is not None:
            return value
        return ['']*self.widget_count

class TUGDutyField(forms.MultiValueField):
    widget = MultiTextInput(widget_count=3)
    _initial_fields = lambda self:(self.weekly, self.total, self.comment) 
    
    def __init__(self, *args, **kwargs):
        self.weekly = forms.DecimalField(label="Weekly hours")
        self.total = forms.DecimalField(label="Total hours")
        self.comment = forms.CharField(label="Comment")
        
        super(TUGDutyField, self).__init__(
                self._initial_fields(), *args, **kwargs)
    def compress(self, data_list):
        # TODO: return a dict of {'weekly': int, 'total': int, 'comment': str}
        assert False, data_list

class TUGDutyFieldOther(forms.MultiValueField):
    widget = MultiTextInput(widget_count=4)
    _initial_fields = lambda self:(self.label_field, 
            self.weekly, self.total, self.comment)
    
    def __init__(self, *args, **kwargs):
        self.label_field = forms.CharField()
        super(TUGDutyFieldOther, self).__init__(
                *args, **kwargs)
    def compress(self, data_list):
        # TODO: like TUGDutyField, return a dict of 
        # {'label': str, 'weekly': int, 'total': int, 'comment': str}
        assert False, data_list

class TUGForm(forms.ModelForm):
    def __init__(self, offering=None, *args, **kwargs):
        super(TUGForm, self).__init__(*args, **kwargs)
        
        # limit the fields in the dropdown
        if offering is None:
            self.fields['member'].queryset = Member.objects.filter(role='TA')
        else:
            self.fields['member'].queryset = Member.objects.filter(
                    role='TA',offering=offering)
            
        self.config_form = TUGForm.ConfigForm()
    
    class Meta:
        model = TUG
        exclude = ['config']
        
    class ConfigForm(forms.Form):
        prep = TUGDutyField(label="Preparation")#, help_text="Preparation for labs/tutorials")
        meetings = TUGDutyField()
        lectures = TUGDutyField()
        tutorials = TUGDutyField()
        office_hours = TUGDutyField()
        grading = TUGDutyField()
        test_prep = TUGDutyField()
        holiday = TUGDutyField()
        
        other1 = TUGDutyFieldOther(required=False)
        other2 = TUGDutyFieldOther(required=False)
    
class TAApplicationForm(forms.ModelForm):
    class Meta:
        model = TAApplication        
