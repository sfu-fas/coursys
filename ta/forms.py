from django import forms
from django.utils.safestring import mark_safe
from django.forms.forms import BoundField
from django.forms.util import ErrorList
from django.utils.datastructures import SortedDict
from coredata.models import Member, CAMPUS_CHOICES
from ta.models import TUG, TAApplication,TAContract, CoursePreference, TACourse, TAPosting, CATEGORY_CHOICES
from ta.util import table_row__Form, update_and_return
from django.core.exceptions import ValidationError
import itertools, decimal, datetime

@table_row__Form
class TUGDutyForm(forms.Form):
    label_editable = False
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, label=''):
        super(TUGDutyForm, self).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix,
                 empty_permitted)
        self.label = label
    
    weekly = forms.DecimalField(label="Weekly hours", required=False)
    weekly.widget.attrs['class'] = u'weekly'
    weekly.manual_css_classes = [u'weekly']
    total = forms.DecimalField(label="Total hours")
    total.widget.attrs['class'] = u'total'
    total.manual_css_classes = [u'total']
    comment = forms.CharField(label="Comment", required=False)
    comment.widget.attrs['class'] = u'comment'
    comment.manual_css_classes = [u'comment']

class TUGDutyLabelForm(forms.Form):
    label = forms.CharField(label="Other:", 
            error_messages={'required': 'Please specify'})
    label.widget.attrs['class'] = u'label-field'

# doesn't simply subclass TUGDutyForm so that the label will be listed first
class TUGDutyOtherForm(TUGDutyLabelForm, TUGDutyForm):
    label_editable = True
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, label=''):
        empty_permitted = empty_permitted or not (initial and initial.get('label'))
        super(TUGDutyOtherForm, self).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix,
                 empty_permitted, label)
        
    
    def as_table_row(self):
        label = self.fields.pop('label')
        html = TUGDutyForm.as_table_row(self)
        self.fields.insert(0, 'label', label)
        return html

class TUGForm(forms.ModelForm):
    '''
    userid and offering must be defined or instance must be defined.
    '''
    class Meta:
        model = TUG
        exclude = ('config',)
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None,
                 offering=None, userid=None):
        super(TUGForm, self).__init__(data, files, auto_id, prefix, initial,
                 error_class, label_suffix, empty_permitted, instance)
        # see old revisions (git id 1d1d2f9) for a dropdown
        if userid is not None and offering is not None:
            member = Member.objects.get(person__userid=userid, offering=offering)
        elif instance is not None:
            member = instance.member
        else:
            assert False
        
        self.initial['member'] = member
        self.fields['member'].widget = forms.widgets.HiddenInput()
        
        self.subforms = SortedDict(
                [(field, klass(prefix=field, data=data, 
                        initial=(instance.config[field] if instance and field in instance.config else
                                initial[field] if initial and field in initial else None),
                        label=TUG.config_meta[field]['label'] if field in TUG.config_meta else '')) 
                    for field, klass in 
                    itertools.chain(((f, TUGDutyForm) for f in TUG.regular_fields),
                            ((f, TUGDutyOtherForm) for f in TUG.other_fields))])
        
    def clean_member(self):
        assert(self.cleaned_data['member'] == self.initial['member'])
        return self.cleaned_data['member']
    def is_valid(self):
        return (all(form.is_valid() for form in self.subforms.itervalues()) 
                and super(TUGForm, self).is_valid())
    def full_clean(self):
        for form in self.subforms.itervalues():
            form.full_clean()
        return super(TUGForm, self).full_clean()
    def clean(self):
        data = super(TUGForm, self).clean()
        try: data['config'] = SortedDict((field, self.subforms[field].cleaned_data) 
                for field in TUG.all_fields)
        except AttributeError: pass
        return data
    def save(self, *args, **kwargs):
        # TODO: load data from config_form into JSONField
#        self.instance
        self.instance.config = self.cleaned_data['config']
        return super(TUGForm, self).save(*args, **kwargs)
    
class TAApplicationForm(forms.ModelForm):
    
    sin = forms.CharField(min_length=9, max_length=9)

    class Meta:
        model = TAApplication
        exclude = ('person','department','skills','campus_preferences','semester')

class CoursePreferenceForm(forms.ModelForm):

    class Meta:
        model = CoursePreference
        exclude = ('app',) 

class TAContractForm(forms.ModelForm):
    #apps = TAApplication.objects.filter(semester=get_semester())
    #person = [app.person for app in apps]
    #self.field['person'].queryset = person
    
    #def __init__(self,my_var,*args,**kwargs):
     #   super(TAContractForm,self).__init__(*args,**kwargs)
    
    
    sin = forms.CharField(min_length=9, max_length=9)
    #position_number = 
    
    class Meta:
        model = TAContract
        exclude = ['pay_per_bu', 'scholarship_per_bu', 'deadline']
                
class TACourseForm(forms.ModelForm):
    class Meta:
        model = TACourse
        exclude = ('contract',) 


# helpers for the TAPostingForm
class LabelTextInput(forms.TextInput):
    "TextInput with a bonus label"
    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelTextInput, self).__init__(*args, **kwargs)
    def render(self, *args, **kwargs):
        return " " + self.label + ": " + super(LabelTextInput, self).render(*args, **kwargs)

class PayWidget(forms.MultiWidget):
    "Widget for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        widgets = [LabelTextInput(label=c[0], attrs={'size': 6}) for c in CATEGORY_CHOICES]
        kwargs['widgets'] = widgets
        super(PayWidget, self).__init__(*args, **kwargs)
    
    def decompress(self, value):
        # should already be a list: if we get here, got nothing.
        return [0]*len(CATEGORY_CHOICES)

class PayField(forms.MultiValueField):
    "Field for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        fields = [forms.CharField(label='foo') for i in CATEGORY_CHOICES ]
        kwargs['fields'] = fields
        kwargs['widget'] = PayWidget()
        super(PayField, self).__init__(*args, **kwargs)

    def compress(self, values):
        return values



class TAPostingForm(forms.ModelForm):
    start = forms.DateField(label="Contract Start", help_text='Default start date for contracts')
    end = forms.DateField(label="Contract End", help_text='Default end date for contracts')
    salary = PayField(label="Salary per BU", help_text="Default pay rates for contracts")
    scholarship = PayField(label="Scholarship per BU", help_text="Default scholarship rates for contracts")
    excluded = forms.MultipleChoiceField(help_text="Courses that should not be selectable for TA positions", choices=[], widget=forms.SelectMultiple(attrs={'size': 15}))

    # TODO: sanity-check the dates against semester start/end
    
    class Meta:
        model = TAPosting
        exclude = ('config',) 
    
    def __init__(self, *args, **kwargs):
        super(TAPostingForm, self).__init__(*args, **kwargs)
        # populat initial data fron instance.config
        self.initial['salary'] = self.instance.salary()
        self.initial['scholarship'] = self.instance.scholarship()
        self.initial['start'] = self.instance.start()
        self.initial['end'] = self.instance.end()
        self.initial['excluded'] = self.instance.excluded()
    
    def clean_start(self):
        start = self.cleaned_data['start']
        self.instance.config['start'] = unicode(start)
        return start

    def clean_end(self):
        end = self.cleaned_data['end']
        if 'start' in self.cleaned_data:
            start = self.cleaned_data['start']
            if start >= end:
                raise forms.ValidationError("Contracts must end after they start")
        self.instance.config['end'] = unicode(end)
        return end
        
    def clean_opens(self):
        opens = self.cleaned_data['opens']
        today = datetime.date.today()
        if opens < today:
            raise forms.ValidationError("Postings cannot open before today")
        return opens

    def clean_closes(self):
        closes = self.cleaned_data['closes']
        today = datetime.date.today()
        if closes <= today:
            raise forms.ValidationError("Postings must close after today")
        if 'opens' in self.cleaned_data:
            opens = self.cleaned_data['opens']
            if opens >= closes:
                raise forms.ValidationError("Postings must close after they open")
        return closes
        
    def clean_salary(self):
        sals = self.cleaned_data['salary']
        try:
            sals = [decimal.Decimal(s).quantize(decimal.Decimal('1.00')) for s in sals]
        except decimal.InvalidOperation:
            raise forms.ValidationError("Salary values must be numbers")
        
        self.instance.config['salary'] = [str(s) for s in sals]
        return sals
    
    def clean_scholarship(self):
        schols = self.cleaned_data['scholarship']
        try:
            schols = [decimal.Decimal(s).quantize(decimal.Decimal('1.00')) for s in schols]
        except decimal.InvalidOperation:
            raise forms.ValidationError("Scholarship values must be numbers")

        self.instance.config['scholarship'] = [str(s) for s in schols]
        return schols
    
    def clean_excluded(self):
        excluded = self.cleaned_data['excluded']
        excluded = [int(e) for e in excluded]
        self.instance.config['excluded'] = excluded
        return excluded
    
