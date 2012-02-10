from django import forms
from django.utils.safestring import mark_safe
from django.forms.forms import BoundField
from django.forms.util import ErrorList
from django.utils.datastructures import SortedDict
from coredata.models import Member, CAMPUS_CHOICES
from ta.models import TUG, TAApplication,TAContract, CoursePreference,TACourse
from ta.util import table_row__Form, update_and_return
from django.core.exceptions import ValidationError
import itertools

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
        
        # we're composing (one form inside of another) forms here, which takes some plumbing
        # for a list of methods that should be chained, run
        #  tf = ta.forms.TUGForm()
        #  tmd = dict(inspect.getmembers(tf, inspect.ismethod)
        #  [(mname, (tmd[mname], method)) 
        #          for mname, method in inspect.getmembers(
        #                  tf.config_form, inspect.ismethod) 
        #          if mname in tmd and mname[0] != '_' and mname[:3] != 'as_']
        # currently, this yields add_prefix, clean, full_clean, is_multipart and is_valid
        # currently, we're chaining clean, full_clean and is_valid
        
        # populate config_form with data or instance data, see TUGDutyForm.__init__
        
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
        exclude = ('person','department','skills','campus_preferences',)

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
        exclude = ['total_bu','pay_per_bu', 'scholarship_per_bu', 'deadline', 'appt_cond', 'appt_tssu' ]

'''        
class TAContractForm2(forms.ModelForm):
    class Meta:
        model = TAContract
        fields = ['total_bu', 'pay_per_bu', 'scholarship_per_bu', 'remarks', 'deadline', 'appt_cond', 'appt_tssu' ]
'''
                
class TACourseForm(forms.ModelForm):
    class Meta:
        model = TACourse
        exclude = ('contract',) 
