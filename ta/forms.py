from django import forms
from django.utils.safestring import mark_safe
from coredata.models import Member
from ta.models import *
from ta.util import table_row__Form
from django.forms.forms import BoundField

@table_row__Form
class TUGDutyForm(forms.Form):
    def __init__(self, label='', label_editable=False, *args, **kwargs):
        super(TUGDutyForm, self).__init__(*args, **kwargs)
        self.label = self.initial['label'] if 'label' in self.initial else label
        self.label_field = None
        self.label_editable = (self.initial['label_editable'] 
                if 'label_editable' in self.initial 
                else label_editable)
        if self.label_editable:
            self.label_field = forms.CharField(label="")
            self.label_field.widget.attrs['class'] = u'label-field'
    
    @property
    def label_bound_field(self):
        return BoundField(self, self.label_field, u'label_field')
        
    weekly = forms.DecimalField(label="Weekly hours")
    weekly.widget.attrs['class'] = u'weekly'
    weekly.manual_css_classes = [u'weekly']
    total = forms.DecimalField(label="Total hours")
    total.widget.attrs['class'] = u'total'
    total.manual_css_classes = [u'total']
    comment = forms.CharField(label="Comment")
    comment.widget.attrs['class'] = u'comment'
    comment.manual_css_classes = [u'comment']

class TUGDutyFormSet(forms.formsets.BaseFormSet):
    # required, since this isn't being dynamically added by formset_factory
    form = TUGDutyForm
    extra = 0
    can_order=False
    can_delete=False
    max_num=None
    
    def __init__(self, *args, **kwargs):
        super(TUGDutyFormSet, self).__init__(*args, **kwargs)
    
    # without the row header, this function could be separated out, like table_row__Form
    # unused by template
    def as_table_row(self):
        "Returns this formset rendered as HTML <tr>s -- excluding the <table></table>."
        # renders each form as a table row with each field as a td.
        row_header = lambda form: (u'<th>' + 
                form.label_field.as_widget() if form.label_editable 
                else form.label + u'</th>')
        forms = u'<tr>' + u'</tr><tr>'.join(
                row_header(form) + form.as_table_row() 
                for form in self) + u'</tr>'
        return mark_safe(u'\n'.join([unicode(self.management_form), row_header, forms]))
    
#class TUGDutyFieldOther(forms.MultiValueField):
#    widget = MultiTextInput(widget_count=4)
#    _initial_fields = lambda self:(self.label_field, 
#            self.weekly, self.total, self.comment)
#    
#    def __init__(self, *args, **kwargs):
#        self.label_field = forms.CharField()
#        super(TUGDutyFieldOther, self).__init__(
#                *args, **kwargs)
#    def compress(self, data_list):
#        # TODO: like TUGDutyField, return a dict of 
#        # {'label': str, 'weekly': int, 'total': int, 'comment': str}
#        assert False, data_list

class TUGForm(forms.ModelForm):
    def __init__(self, offering=None, userid=None, *args, **kwargs):
        super(TUGForm, self).__init__(*args, **kwargs)
        
        # limit the fields in the dropdown
        # userid should be passed but if for some reason it isn't filter by offering
        # if offering is also missing, display all TAs as final fallback
        # otherwise, filter both both.
        if userid is not None:
            memberQuerylist = Member.objects.filter(person__userid=userid)
            if not offering is None:
                memberQuerylist = memberQuerylist.filter(offering=offering)
        else: 
            if offering is None:
                memberQuerylist = Member.objects.filter(role='TA')
            else:
                memberQuerylist = Member.objects.filter(role='TA',offering=offering)
        
        self.fields['member'].queryset = memberQuerylist
        
        self.config_form = TUGDutyFormSet(initial=
                [TUG.config_meta[field] for field in TUG.regular_fields]+
                [{'label':field, 'label_editable':True} for field in TUG.other_fields])
    
    class Meta:
        model = TUG
        exclude = ['config']
    
#    class ConfigForm(forms.Form):
#        prep = TUGDutyField(label="Preparation")#, help_text="Preparation for labs/tutorials")
#        meetings = TUGDutyField()
#        lectures = TUGDutyField()
#        tutorials = TUGDutyField()
#        office_hours = TUGDutyField()
#        grading = TUGDutyField()
#        test_prep = TUGDutyField()
#        holiday = TUGDutyField()
#        
#        other1 = TUGDutyField(required=False)
#        other2 = TUGDutyField(required=False)
    
class TAApplicationForm(forms.ModelForm):
    class Meta:
        model = TAApplication        
