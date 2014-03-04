import re
from django import forms
#from django.utils.safestring import mark_safe
#from django.forms.forms import BoundField
from django.forms.util import ErrorList
from django.utils.datastructures import SortedDict
from coredata.models import Member
from ta.models import TUG, TAApplication,TAContract, CoursePreference, TACourse, TAPosting, Skill, \
        CourseDescription, CATEGORY_CHOICES, STATUS_CHOICES
from ta.util import table_row__Form
#from django.core.exceptions import ValidationError
import itertools, decimal, datetime
from django.forms.formsets import formset_factory
from django.forms.models import BaseInlineFormSet
from pages.forms import WikiField

class LabelledHidden(forms.HiddenInput):
    """
    A hidden input where the field is displayed, but without any way to edit.
    
    Used to make fixed fields on TUG non-editable.
    """
    input_type = 'hidden'
    is_hidden = False
    def render(self, name, value, attrs=None):
        res = super(LabelledHidden, self).render(name, value, attrs=attrs) 
        if value:
            res += unicode(value)
        return res

@table_row__Form
class TUGDutyForm(forms.Form):
    label_editable = False
    def __init__(self, *args, **kwargs):
        label = kwargs.pop('label', '')
        super(TUGDutyForm, self).__init__(*args, **kwargs)
        self.label = label
    
    weekly = forms.DecimalField(label="Weekly hours", required=False)
    weekly.widget.attrs['class'] = u'weekly'
    weekly.manual_css_classes = [u'weekly']
    total = forms.DecimalField(label="Total hours", 
            error_messages={'required':u'Number of hours is required.'})
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
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', None)
        # allow empty if this is a new TUG or if we're editing and it's empty
        kwargs['empty_permitted'] = (kwargs.get('empty_permitted', False) or
                (initial and bool(initial.get('label'))))
        super(TUGDutyOtherForm, self).__init__(*args, **kwargs)
        self.fields['label'].required = False
        self.fields['total'].required = False
        
    def as_table_row(self):
        label = self.fields.pop('label')
        html = TUGDutyForm.as_table_row(self)
        self.fields.insert(0, 'label', label)
        return html
    
    def clean(self):
        data = self.cleaned_data
        if (data.get('total', None) or data.get('weekly', None)) and not data.get('label', None):
            e = forms.ValidationError('A label is required.')
            self._errors['label'] = self.error_class(e.messages)
            raise forms.ValidationError([])
            
        if (data.get('label') and not (data.get('total', None))):
            e = forms.ValidationError(self.fields['total'].error_messages['required'])
            self._errors['total'] = self.error_class(e.messages)
            raise forms.ValidationError([])
        
        return super(TUGDutyOtherForm, self).clean()

class TUGForm(forms.ModelForm):
    '''
    userid and offering must be defined or instance must be defined.
    '''
    base_units = forms.DecimalField(min_value=0, 
            error_messages={"min_value":"Base units must be positive.",
                            "invalid":"Base units must be a number.",
                            "required":"Base units are required."})
    
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
            member = Member.objects.exclude(role='DROP').get(person__userid=userid, offering=offering)
        elif instance is not None:
            member = instance.member
        else:
            assert False
        
        self.initial['member'] = member
        self.fields['member'].widget = forms.widgets.HiddenInput()
        
        self.subforms = self.__construct_subforms(data, initial, instance)
        
    def __construct_subforms(self, data, initial, instance):
        # this function is a simplification/clarification of this one liner:
        # return SortedDict((field, klass(prefix=field, data=data, 
        #  initial=(instance.config[field] if instance and field in instance.config 
        #  else initial[field] if initial and field in initial else None), 
        #  label=TUG.config_meta[field]['label'] if field in TUG.config_meta else '')) 
        #  for field, klass in itertools.chain(((f, TUGDutyForm) for f in TUG.regular_fields), 
        #  ((f, TUGDutyOtherForm) for f in TUG.other_fields)))
        field_names_and_formclasses = itertools.chain(
                ((f, TUGDutyForm) for f in TUG.regular_fields),
                ((f, TUGDutyOtherForm) for f in TUG.other_fields))
        
        get_label = lambda field: TUG.config_meta[field]['label'] if field in TUG.config_meta else ''
        
        get_initial = lambda field: None
        if instance:
            if initial:
                get_initial = lambda field:(instance.config[field] 
                        if field in instance.config else 
                        initial.get(field, None))
            else:
                get_initial = lambda field:instance.config.get(field, None)
        elif initial:
            get_initial = lambda field:initial.get(field, None)
        
        return SortedDict(
                (field, 
                 klass(prefix=field, data=data, 
                       initial=get_initial(field),
                       label=get_label(field))) 
                    for field, klass in field_names_and_formclasses)
        
    def clean_member(self):
        if self.cleaned_data['member'] != self.initial['member']:
            raise forms.ValidationError("Wrong member")
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
        get_data = lambda subform: subform.cleaned_data if subform.cleaned_data else subform.initial
        try: data['config'] = SortedDict((field, get_data(self.subforms[field])) 
                for field in TUG.all_fields)
        except AttributeError:
            raise forms.ValidationError([])
        return data
    def save(self, *args, **kwargs):
        self.instance.config = self.cleaned_data['config']
        return super(TUGForm, self).save(*args, **kwargs)

class TAApplicationForm(forms.ModelForm):
    sin_default = '000000000'
    class Meta:
        model = TAApplication
        exclude = ('posting','person','skills','campus_preferences','rank','late','admin_created', 'config')
        widgets = {'base_units': forms.TextInput(attrs={'size': 5}),
                   'current_program': forms.TextInput(attrs={'size': 10}),
                   'experience': forms.Textarea(attrs={'cols': 50, 'rows': 3}),
                   'course_load': forms.Textarea(attrs={'cols': 50, 'rows': 2}),
                   'other_support': forms.Textarea(attrs={'cols': 50, 'rows': 2}),
                   'comments': forms.Textarea(attrs={'cols': 50, 'rows': 3}),
                   }

    def __init__(self, *args, **kwargs):
        super(TAApplicationForm, self).__init__(*args, **kwargs)
        self.fields['sin'].help_text = 'Social insurance number (required for receiving payments: if you don\'t have a SIN yet, please enter "000000000".)'
        self.fields['sin'].required = True
        self.fields['current_program'].required = True

    def add_extra_questions(self, posting):
        if 'extra_questions' in posting.config and len(posting.config['extra_questions']) > 0:
            for question in posting.config['extra_questions']:
                if 'extra_questions' in self.instance.config and question in self.instance.config['extra_questions']:
                    self.fields[question.encode('ascii', 'ignore')] = forms.CharField(label="Question", help_text=question, widget=forms.Textarea, initial=self.instance.config['extra_questions'][question])
                else:
                    self.fields[question.encode('ascii', 'ignore')] = forms.CharField(label="Question", help_text=question, widget=forms.Textarea)

    def clean_sin(self):
        sin = self.cleaned_data['sin']
        if sin.strip() == '':
            sin = self.sin_default
        else:
            sin = re.sub('[ -]+','',str(sin))
            if not re.match('\d{9}$',sin):
                raise forms.ValidationError("Invalid SIN")
        return sin

    def clean_base_units(self):
        bu = self.cleaned_data['base_units']
        if bu > 5 or bu < 1:
            raise forms.ValidationError("BU amount must be in the range 1-5")
        return bu

class CoursePreferenceForm(forms.ModelForm):

    class Meta:
        model = CoursePreference
        exclude = ('app','rank') 
        
class TAAcceptanceForm(forms.ModelForm):
    sin = forms.CharField(label="SIN", help_text="Social insurance number")
       
    class Meta:
        model = TAContract
        fields = ['sin']
    
class NewTAContractForm(forms.Form):
    application = forms.ModelChoiceField(queryset=TAApplication.objects.none())


class TAContractForm(forms.ModelForm):
 
    #pay_per_bu = forms.DecimalField(max_digits=8, decimal_places=2)
    #scholarship_per_bu = forms.DecimalField(max_digits=8, decimal_places=2) 
          
    def __init__(self, *args, **kwargs):
        super(TAContractForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance.id and instance.sin == '000000000':
            self.fields['sin'].help_text = "Valid SIN is required for receiving payments"

    class Meta:
        model = TAContract
        exclude = ['posting', 'application', 'created_by']
        widgets = {'remarks': forms.Textarea(attrs={'rows': 3, 'cols': 60}), }
        
        
    def clean_pay_per_bu(self):
        pay = self.cleaned_data['pay_per_bu']
        try:
            pay = decimal.Decimal(pay).quantize(decimal.Decimal('1.00'))
 
            
        except decimal.InvalidOperation:
            raise forms.ValidationError("Pay per BU values must be numbers")
        return pay
    
    def clean_scholarship_per_bu(self):
        schol = self.cleaned_data['scholarship_per_bu']
        try:
            schol = decimal.Decimal(schol).quantize(decimal.Decimal('1.00'))
        except decimal.InvalidOperation:
            raise forms.ValidationError("Scholarship per BU values must be numbers")
        return schol
        
    def clean_sin(self):
        sin = self.cleaned_data['sin']
        sin = re.sub('[ -]+','',str(sin))
        if not re.match('\d{9}$',sin):
            raise forms.ValidationError("Invalid SIN")
        return sin
        
    def clean_pay_start(self):
        start = self.cleaned_data['pay_start']
        return start

    def clean_pay_end(self):
        end = self.cleaned_data['pay_end']
        if 'pay_start' in self.cleaned_data:
            start = self.cleaned_data['pay_start']
            if start >= end:
                raise forms.ValidationError("Contracts must end after they start")
        return end
    
    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        today = datetime.date.today()
        if deadline < today:
            raise forms.ValidationError("Deadline for acceptance cannot be before today")
        return deadline
    
class TACourseForm(forms.ModelForm):           
    class Meta:
        model = TACourse
        exclude = ('contract',)
        widgets = {'course': forms.Select(attrs={'class': 'course_select'}),
                   'description': forms.Select(attrs={'class': 'desc_select'}),
                   'bu': forms.TextInput(attrs={'class': 'bu_inp'})
                   }

class BaseTACourseFormSet(BaseInlineFormSet):    
    def clean(self):
        self.validate_unique()
        
        #check at least one course selected
        count = 0
        if any(self.errors):
            return
        for form in self.forms:
            try:
                if form.cleaned_data:
                    count += 1
            except AttributeError:
                pass
        if count < 1:
            raise forms.ValidationError(u"Please select at least one course")
        
        #check no duplicate course selection
        courses = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['course']:
                course = form.cleaned_data['course']
                if(course in courses):
                        raise forms.ValidationError(u"Duplicate course selection")
                courses.append(course)  
        
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
        # should already be a list: if we get here, have no defaults
        return [0]*len(CATEGORY_CHOICES)
class PayField(forms.MultiValueField):
    "Field for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        fields = [forms.CharField() for _ in CATEGORY_CHOICES]
        kwargs['fields'] = fields
        kwargs['widget'] = PayWidget()
        super(PayField, self).__init__(*args, **kwargs)

    def compress(self, values):
        return values

from ra.models import Account
class LabelSelect(forms.Select):
    "Select with a bonus label"
    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelSelect, self).__init__(*args, **kwargs)
    def render(self, *args, **kwargs):
        return " " + self.label + ": " + super(LabelSelect, self).render(*args, **kwargs)
class AccountsWidget(forms.MultiWidget):
    "Widget for selecting Account values"
    def __init__(self, *args, **kwargs):
        widgets = [LabelSelect(label=c[0]) for c in CATEGORY_CHOICES]
        kwargs['widgets'] = widgets
        super(AccountsWidget, self).__init__(*args, **kwargs)
    
    def decompress(self, value):
        # should already be a list: if we get here, have no defaults
        return [0]*len(CATEGORY_CHOICES)
class AccountsField(forms.MultiValueField):
    "Field for selecting Account values"
    def __init__(self, *args, **kwargs):
        fields = [forms.ModelChoiceField(Account.objects.all()) for _ in CATEGORY_CHOICES]
        kwargs['fields'] = fields
        kwargs['widget'] = AccountsWidget()
        super(AccountsField, self).__init__(*args, **kwargs)

    def compress(self, values):
        return values

class TAPostingForm(forms.ModelForm):
    deadline = forms.DateField(label="Acceptance Deadline", 
        help_text='Default deadline for apointees to accept/decline contracts')
    start = forms.DateField(label="Contract Start", 
        help_text='Default start date for contracts')
    end = forms.DateField(label="Contract End", 
        help_text='Default end date for contracts')
    salary = PayField(label="Salary per BU", 
        help_text="Default pay rates for contracts")
    scholarship = PayField(label="Scholarship per BU", 
        help_text="Default scholarship rates for contracts")
    accounts = AccountsField(label="Position Number", 
        help_text="Default position number for contracts")
    payperiods = forms.DecimalField(label="Pay periods", 
        help_text='Number of pay periods in the semester',
        max_value=20, min_value=1, widget=forms.TextInput(attrs={'size': 5}))
    contact = forms.ChoiceField(label="Contact Person", 
        help_text="Person to give applicants/offers to ask questions.")
    max_courses = forms.IntegerField(label="Maximum courses", 
        help_text="The maximum number of courses an applicant can specify.")
    min_courses = forms.IntegerField(label="Minimum courses", 
        help_text="The minimum number of courses an applicant can specify.")
    excluded = forms.MultipleChoiceField(
        help_text="Courses that should <strong>not</strong> be selectable for TA positions",
        choices=[], required=False, widget=forms.SelectMultiple(attrs={'size': 15}))
    skills = forms.CharField(label="Skills", required=False, widget=forms.Textarea(),
        help_text='Skills to ask applicants about: one per line')
    extra_questions = forms.CharField(label="Extra Questions", required=False,
        help_text='Extra questions to ask applicants: one per line',
        widget=forms.Textarea())
    instructions = forms.CharField(label="Instructions", 
        help_text='Additional instructions for students filling out the application.',
        required=False, widget=forms.Textarea())
    hide_campuses = forms.BooleanField(label="Hide Campuses", initial=False, 
        required=False,
        help_text='Do not prompt students for their Campus choice.')
    offer_text = WikiField(label="Offer Text", required=False, 
        help_text='Presented as "More Information About This Offer"; formatted in <a href="/docs/pages">WikiCreole markup</a>.')

    # TODO: sanity-check the dates against semester start/end
    
    class Meta:
        model = TAPosting
        exclude = ('config',) 
    
    def __init__(self, *args, **kwargs):
        super(TAPostingForm, self).__init__(*args, **kwargs)
        # populate initial data fron instance.config
        self.initial['salary'] = self.instance.salary()
        self.initial['scholarship'] = self.instance.scholarship()
        self.initial['start'] = self.instance.start()
        self.initial['accounts'] = self.instance.accounts()
        self.initial['end'] = self.instance.end()
        self.initial['deadline'] = self.instance.deadline()
        self.initial['excluded'] = self.instance.excluded()
        self.initial['max_courses'] = self.instance.max_courses()
        self.initial['min_courses'] = self.instance.min_courses()
        self.initial['payperiods'] = decimal.Decimal(self.instance.payperiods())
        self.initial['contact'] = self.instance.contact().id
        self.initial['offer_text'] = self.instance.offer_text()
        skills = Skill.objects.filter(posting=self.instance)
        self.initial['extra_questions'] = '\n'.join(self.instance.extra_questions())
        self.initial['skills'] = '\n'.join((s.name for s in skills))
        self.initial['instructions'] = self.instance.instructions()
        self.initial['hide_campuses'] = self.instance.hide_campuses()
    
    def clean_payperiods(self):
        payperiods = self.cleaned_data['payperiods']
        self.instance.config['payperiods'] = payperiods
        return payperiods

    def clean_contact(self):
        contact = self.cleaned_data['contact']
        self.instance.config['contact'] = contact
        return contact

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

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        self.instance.config['deadline'] = unicode(deadline)
        return deadline
        
    def clean_opens(self):
        opens = self.cleaned_data['opens']
        #today = datetime.date.today()
        #if opens < today:
        #    raise forms.ValidationError("Postings cannot open before today")
        return opens

    def clean_closes(self):
        closes = self.cleaned_data['closes']
        #today = datetime.date.today()
        #if closes <= today:
        #    raise forms.ValidationError("Postings must close after today")
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

    def clean_accounts(self):
        accounts = self.cleaned_data['accounts']
        self.instance.config['accounts'] = [a.id for a in accounts]
        return [a.id for a in accounts]
    
    def clean_max_courses(self):
        max_courses = self.cleaned_data['max_courses']
        self.instance.config['max_courses'] = max_courses
        return max_courses
    
    def clean_min_courses(self):
        min_courses = self.cleaned_data['min_courses']
        max_courses = self.cleaned_data['max_courses']
        self.instance.config['min_courses'] = min_courses
        if max_courses < min_courses:
            raise forms.ValidationError("Maximum courses must be greater than Minimum courses")
        return min_courses
    
    def clean_excluded(self):
        excluded = self.cleaned_data['excluded']
        excluded = [int(e) for e in excluded]
        self.instance.config['excluded'] = excluded
        return excluded

    def clean_offer_text(self):
        offer_text = self.cleaned_data['offer_text']
        self.instance.config['offer_text'] = offer_text
        return offer_text
    
    def clean_skills(self):
        skills = self.cleaned_data['skills']
        skills = [s.strip() for s in skills.split("\n") if len(s.strip()) > 0]
        old_skills = Skill.objects.filter(posting=self.instance)
        res = []
        for i, skill in enumerate(skills):
            if len(old_skills) < i+1:
                # nothing existing
                new = Skill(posting=self.instance, name=skill, position=i)
                res.append(new)
            else:
                # update old
                old = old_skills[i]
                old.name = skill
                res.append(old)
        return res

    def clean_extra_questions(self):
        extra_questions = self.cleaned_data['extra_questions']
        extra_questions = [q.strip().encode('ascii', 'ignore') for q in extra_questions.split('\n') if len(q.strip()) > 0 ]
        self.instance.config['extra_questions'] = extra_questions
        return extra_questions

    def clean_instructions(self):
        instructions = self.cleaned_data['instructions']
        self.instance.config['instructions'] = instructions
        return instructions

    def clean_hide_campuses(self):
        hide_campuses = self.cleaned_data['hide_campuses']
        self.instance.config['hide_campuses'] = hide_campuses
        return hide_campuses

class BUForm(forms.Form):
    students = forms.IntegerField(min_value=0, max_value=1000)
    bus = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2)

BUFormSet = formset_factory(BUForm, extra=10)
LEVEL_CHOICES = (
                 ('100', '100-level'),
                 ('200', '200-level'),
                 ('300', '300-level'),
                 ('400', '400-level'),
                 )
class TAPostingBUForm(forms.Form):
    level = forms.ChoiceField(choices=LEVEL_CHOICES)

class AssignBUForm(forms.Form):
    rank = forms.IntegerField(min_value=0, label="rank")
    rank.widget.attrs['size'] = '2'
    bu = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, required=False)
    bu.widget.attrs['class'] = u'bu_inp'
    bu.widget.attrs['size'] = '3'

# fake contract statuses to allow selecting applicants in the form
APPLICANT_STATUSES = (('_APPLIC', 'Applicants (not late)'), ('_LATEAPP', 'Late Applicants'))
class TAContactForm(forms.Form):
    statuses = forms.MultipleChoiceField(choices=APPLICANT_STATUSES+STATUS_CHOICES, help_text="TAs to contact (according to contract status)")
    subject = forms.CharField()
    text = forms.CharField(widget=forms.Textarea(), help_text='Message body. <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed.')
    url = forms.URLField(label="URL", required=False, help_text='Link to include in the message. (optional)')


class CourseDescriptionForm(forms.ModelForm):
    class Meta:
        model = CourseDescription
        exclude = ('config','hidden') 
