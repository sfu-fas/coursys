from django import forms
from django.utils.safestring import mark_safe
from coredata.models import Member, CAMPUS_CHOICES
from ta.models import *
from ta.util import table_row__Form
from django.forms.forms import BoundField
from django.forms.util import ErrorList
import copy

@table_row__Form
class TUGDutyForm(forms.Form):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False,
                 label='', label_editable=False):
        
        # set data field if it's defined in initial, see TUGForm.__init__
        if initial and 'data' in initial and initial['data'] is not None:
            self.prefix = prefix # needed for add_prefix
            data = dict((self.add_prefix(field_name), value)
                    for field_name, value in initial['data'].iteritems())
        
        super(TUGDutyForm, self).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix,
                 empty_permitted)
        
        self.label = (data['label'] if data and 'label' in data else 
                self.initial['label'] if 'label' in self.initial else label)
        self.label_field = None
        self.label_editable = (self.initial['label_editable'] 
                if 'label_editable' in self.initial 
                else label_editable)
        if self.label_editable:
            self.label_field = forms.CharField(label="")
            self.label_field.widget.attrs['class'] = u'label-field'
    
    @property
    def label_bound_field(self):
        return BoundField(self, self.label_field, u'label')
        
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
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList):
        super(TUGDutyFormSet, self).__init__(data, files, auto_id, prefix,
                 initial, error_class)
        self.forms_dict = {}
        for form in self.forms:
            if 'id' in form.initial:
                self.forms_dict[form.initial['id']] = form
    
    def __getitem__(self, index):
        if index in self.forms_dict:
            return self.forms_dict[index]
        return super(TUGDutyFormSet, self).__getitem__(index)
    
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
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None,
                 offering=None, userid=None):
        super(TUGForm, self).__init__(data, files, auto_id, prefix, initial,
                 error_class, label_suffix, empty_permitted, instance)
        
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
        
        def update_and_return(d, other):
            d.update(other)
            return d
        
        # populate config_form with data or instance data, see TUGDutyForm.__init__
        self.config_form = TUGDutyFormSet(initial=
                [update_and_return(
                        {'id':field, 
                         'data':(data.get(field, None) if data is not None else 
                                 instance.__getattribute__(field) if instance else None)},
                        TUG.config_meta[field]) 
                        for field in TUG.regular_fields] +
                [{'id':field, 'label':field, 'label_editable':True,
                        'data':(data.get(field, None) if data is not None else
                                instance.__getattribute__(field) if instance else None)} 
                        for field in TUG.other_fields])
    
    class Meta:
        model = TUG
        exclude = ['config']
    
class TAApplicationForm(forms.ModelForm):
    
    sin = forms.CharField(min_length=9, max_length=9)
    campus_prefered = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=CAMPUS_CHOICES)

    class Meta:
        model = TAApplication
        exclude = ('person','skills',)
