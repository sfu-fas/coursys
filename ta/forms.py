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
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False):
        self.label_editable = not (initial is not None and 'id' in initial and
                                   initial['id'] in TUG.regular_fields)
        # empty is permitted if this is an 'other' field and we're not editing it
        empty_permitted = empty_permitted or (self.label_editable and 
                not (initial is not None and 'label' in initial))
        super(TUGDutyForm, self).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix,
                 empty_permitted)
        self.label = self.initial['label'] if 'label' in self.initial else ''
        
        self.label_field = self.fields.pop('label')
        if not self.label_editable:
            del self.label_field
    
    @property
    def label_bound_field(self):
        return BoundField(self, self.label_field, u'label')
    
    label = forms.CharField(label="Other:", 
            error_messages={'required': 'Please specify'})
    label.widget.attrs['class'] = u'label-field'
    weekly = forms.DecimalField(label="Weekly hours", required=False)
    weekly.widget.attrs['class'] = u'weekly'
    weekly.manual_css_classes = [u'weekly']
    total = forms.DecimalField(label="Total hours")
    total.widget.attrs['class'] = u'total'
    total.manual_css_classes = [u'total']
    comment = forms.CharField(label="Comment", required=False)
    comment.widget.attrs['class'] = u'comment'
    comment.manual_css_classes = [u'comment']
    
    def clean(self):
        data = super(TUGDutyForm, self).clean()
        # add label data to cleaned data
        if self.label_editable:
            value = self.label_field.widget.value_from_datadict(
                        self.data, self.files, self.add_prefix('label'))
            try:
                data['label'] = self.label_field.clean(value)
            except ValidationError, e:
                self._errors['label'] = self.error_class(e.messages)
        # TODO: (maybe) make sure that hours per week makes sense
        return data

class BaseTUGDutyFormSet(forms.formsets.BaseFormSet):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList):
        super(BaseTUGDutyFormSet, self).__init__(data, files, auto_id, prefix,
                 initial, error_class)
        self.forms_dict = SortedDict()
        for form in self.forms:
            if 'id' in form.initial:
                self.forms_dict[form.initial['id']] = form
    
    def __getitem__(self, index):
        if index in self.forms_dict:
            return self.forms_dict[index]
        return super(BaseTUGDutyFormSet, self).__getitem__(index)
    
    def _get_cleaned_data(self):
        """
        Overrides default formset cleaned data
        Returns a SortedDict of form.cleaned_data dicts for every form in self.forms.
        """
        if not self.is_valid():
            raise AttributeError("'%s' object has no attribute 'cleaned_data'" % self.__class__.__name__)
        counter = itertools.count(1)
        # count number of preexisting "other" fields
        for form in self.forms:
            if 'id' in form.initial and form.initial['id'].startswith('other'):
                counter.next()
        
        return SortedDict(
                (form.initial['id'] if 'id' in form.initial 
                else 'other%s' % counter.next(), form.cleaned_data) 
                for form in self.forms)
    cleaned_data = property(_get_cleaned_data)
    
TUGDutyFormSet = forms.formsets.formset_factory(TUGDutyForm, extra=0,
        formset = BaseTUGDutyFormSet)

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
        
        if instance:
            # flatten nested (sorted)dict into a list of dicts
            config_form_initial = [update_and_return({'id':k},v,
                                   TUG.config_meta.get(k, {})) 
                                   for k, v in instance.iterfielditems()]
        else:
            config_form_initial = ([update_and_return({'id':field}, TUG.config_meta[field])
                                    for field in TUG.regular_fields] + 
                                   [{'id':field} for field in TUG.other_fields])
        self.config_form = TUGDutyFormSet(initial=config_form_initial, data=data)
        
    def __getitem__(self, name):
        try:
            return super(TUGForm, self).__getitem__(name)
        except KeyError as error:
            try:
                return self.config_form[name]
            except KeyError:
                raise error
    def clean_member(self):
        assert(self.cleaned_data['member'] == self.initial['member'])
        return self.cleaned_data['member']
    def is_valid(self):
        return self.config_form.is_valid() and super(TUGForm, self).is_valid()
    def full_clean(self):
        self.config_form.full_clean()
        return super(TUGForm, self).full_clean()
    def clean(self):
        data = super(TUGForm, self).clean()
        try: data['config'] = self.config_form.cleaned_data
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
    
