from django.forms.models import ModelForm
from django import forms
import grad.models as gradmodels
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus,\
    GradRequirement, CompletedRequirement, LetterTemplate, Letter
from coredata.models import Person, Member, Semester, CAMPUS_CHOICES
from django.forms.formsets import BaseFormSet
from django.core.exceptions import ValidationError
from django.forms.widgets import NullBooleanSelect

class LabelTextInput(forms.TextInput):
    "TextInput with a bonus label"
    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelTextInput, self).__init__(*args, **kwargs)
    def render(self, *args, **kwargs):
        return " " + self.label + ": " + super(LabelTextInput, self).render(*args, **kwargs)

class SupervisorWidget(forms.MultiWidget):
    "Widget for entering supervisor by choices or userid"
    def __init__(self, *args, **kwargs):
        widgets = [forms.Select(), LabelTextInput(label=" or User ID", attrs={'size': 8, 'maxlength': 8})]
        kwargs['widgets'] = widgets
        super(SupervisorWidget, self).__init__(*args, **kwargs)
    
    def decompress(self, value):
        if value:
            return [value, '']
        return [None,None]

class SupervisorField(forms.MultiValueField):
    "Field for entering supervisor by either dropdown or userid"
    def __init__(self, *args, **kwargs):
        fields = [forms.ChoiceField(), forms.CharField(max_length=8)]
        kwargs['fields'] = fields
        kwargs['widget'] = SupervisorWidget()
        super(SupervisorField, self).__init__(*args, **kwargs)

    def compress(self, values):
        """
        Normalize multiselect to a Person object (or None)
        """
        if len(values)<2:
            return None

        try:
            person_id = int(values[0])
        except ValueError:
            person_id = None
        userid = values[1]

        choices = dict(self.fields[0].choices)
        person = None
        if person_id in choices:
            # have a person from the choices
            person = Person.objects.get(id=person_id)
            if userid:
                raise forms.ValidationError("Can't both select person and specify user ID.")
        elif userid:
            # try to find the userid
            try:
                person = Person.objects.get(userid=userid)
            except Person.DoesNotExist:
                raise forms.ValidationError("Unknown user ID.")
        return person


class SupervisorForm(ModelForm):
    supervisor = SupervisorField(required=False)
    
    def set_supervisor_choices(self, choices):
        """
        Set choices for the supervisor
        """
        self.fields['supervisor'].fields[0].choices = [("","Other")] + choices
        self.fields['supervisor'].widget.widgets[0].choices = [("","Other")] + choices

    def clean(self):
        data = self.cleaned_data
        if 'supervisor' in data and not data['supervisor'] == None:
            if data['external']:
                raise forms.ValidationError("Please enter only one of Supervisor or an External supervisor.")
        else:
            if not data['external']:
                print "No supervisor data has been passed. Treat form as empty"
                #raise forms.ValidationError("Please have at least one of Supervisor or an External supervisor.")
        return data
    
    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'created_by', 'modified_by', 'removed')
        
class PotentialSupervisorForm(ModelForm): 
    def set_supervisor_choices(self, choices):
        self.fields['supervisor'].choices = choices

    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'position', 'created_by', 'modified_by', 'external', 'removed')


def possible_supervisors(units, extras=[]):
    """
    .choices list of people who might supervise grad students in these units.
    Extras to indicate values you know about (e.g. the current value(s))
    
    Selects instructors in those units (who still have active computing accounts)
    """
    # instructors of courses in the unit
    people = set(m.person for m in
             Member.objects.filter(role="INST", offering__owner__in=units).select_related('person')
             .exclude(offering__component="SEC") if m.person.userid)
    # previous supervisors
    #people |= set(s.supervisor for s in
    #          Supervisor.objects.filter(student__program__unit__in=units).select_related('supervisor') 
    #          if s.supervisor and s.supervisor.userid)
    
    people |= set(extras)
    people = list(people)
    people.sort()
    return [(p.id, p.name()) for p in people]

class BaseSupervisorsFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        supervisors = []
        # Create supervisors array based on data
        # if there are any empty forms before non-empty forms
        # display validation error
        for i in range(0,self.total_form_count()):
            form = self.forms[i]
            if (form.cleaned_data['supervisor'] != None):
                supervisors.insert(i,form.cleaned_data['supervisor'])
            elif form.cleaned_data['external'] != None and form.cleaned_data['external'] != '':
                supervisors.insert(i,form.cleaned_data['external'])
            else:
                supervisors.insert(i,None)

        for i in range(len(supervisors)):
            for j in range(len(supervisors)):
                if i<j and supervisors[j] != None and supervisors[i] == None:
                    raise forms.ValidationError("Please fill in supervisor forms in order.")
        
                    

class GradAcademicForm(ModelForm):
    class Meta: 
        model = GradStudent
        fields = ('program', 'research_area', 'campus', 'english_fluency', 'mother_tongue', 'is_canadian', 'passport_issued_by', 'special_arrangements', 'comments')

class GradProgramForm(ModelForm):
    class Meta:
        model = GradProgram
        exclude = ('created_by', 'modified_by' )        
        
class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
        exclude = ('created_by', 'modified_by' )
        
class GradStatusForm(ModelForm):
    class Meta:
        model = GradStatus
        exclude = ('student', 'created_by', 'hidden')
        hidden = ('id')

class GradRequirementForm(ModelForm):
    class Meta:
        model = GradRequirement

class CompletedRequirementForm(ModelForm):
    class Meta:
        model = CompletedRequirement
        fields = ('requirement', 'semester', 'date', 'notes')

class LetterTemplateForm(ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'25', 'cols': '100'}))    
    class Meta:
        model = LetterTemplate
        exclude = ('created_by')

class LetterForm(ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'25', 'cols': '100'})) 
    class Meta: 
        model = Letter
        exclude = ('created_by', 'config')

def choices_with_negate(choices):
    return (list(choices) + [('NOT_' + k, 'Not ' + v) for k, v in choices])

class NullBooleanSelect_Optional(NullBooleanSelect):
    def __init__(self, *args, **kwargs):
        super(NullBooleanSelect_Optional, self).__init__(*args, **kwargs)
        self.choices = [(u'', '---------')] + self.choices

class NullBooleanSelect_Filter(NullBooleanSelect):
    def __init__(self, attrs=None):
        choices = ((u'', '---------'), (u'2', 'Yes'), (u'3', 'No'))
        super(NullBooleanSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u''
        return super(NullBooleanSelect_Filter, self).render(name, value, attrs, choices)

# should be moved into whatever model this is stored in
# This is also a guess at which statuses are mutually exclusive
ACCEPTED_CHOICES = (
        ('REJT', 'Rejected'),
        ('DECL', 'Declined Offer'),
        ('EXPI', 'Expired'),
        ('CONF', 'Confirmed'),
        ('CANC', 'Cancelled'),
        ('UNKN', 'Unknown'),
        )

DATE_CHOICES = (('','---------'),
        ('GPRC', 'Grad Program Created'),
        ('GPRU', 'Grad Program Updated'),
        ('GSTC', 'Grad Student Created'),
        ('GSTU', 'Grad Student Updated'),
        ('GSAC', 'Grad Status Created'),
        ('GSAU', 'Grad Status Updated'),
        )

COMMENTS_CHOICES = (
        ('FINC','Financial Comments'),
        ('GRAD','Grad Sec Comments'),
        ('POST','Post Grad Comments'),
        )

class SearchForm(forms.Form):
    #TODO: finish
    
    date_from = forms.DateField(required=False) 
    date_to = forms.DateField(required=False)
    date_search_type = forms.ChoiceField(DATE_CHOICES, required=False,
            help_text='Not Implemented')
    
    start_semester = forms.ModelChoiceField(Semester.objects.all(), required=False,
            help_text='Semester in which the Grad student has applied to start')
    end_semester = forms.ModelChoiceField(Semester.objects.all(), required=False)
    
    # requirements?
    student_status = forms.MultipleChoiceField(gradmodels.STATUS_CHOICES,
#            widget=forms.CheckboxSelectMultiple,
            required=False,
            help_text='Uses "or", selecting nothing means any'
            )
    accepted_status = forms.MultipleChoiceField(ACCEPTED_CHOICES, required=False,
            help_text='Not Implemented; Uses "or", selecting nothing means any')
    archive_sp = forms.NullBooleanField(required=False, 
            widget=NullBooleanSelect_Filter,
            help_text='Not Implemented')
    has_comments = forms.MultipleChoiceField(COMMENTS_CHOICES, required=False,
            help_text='Not Implemented; Uses "or", selecting nothing means any')
    
    #program = forms.CharField(required=False)
    program = forms.ModelChoiceField(GradProgram.objects.all(), required=False)
#    degree = forms.ChoiceField(choices=(
#            ('','---------'),
#            ('INTL','International'),
#            ('CAN','Canadian')
#            ), required=False)
    is_canadian = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
    
    has_financial_support = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter,
            help_text='Not Implemented')
    campus = forms.MultipleChoiceField(CAMPUS_CHOICES, required=False,
            help_text='Uses "or", selecting nothing means any')
    gpa_min = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gpa_max = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False,
            help_text='Not Implemented')
    gender = forms.ChoiceField((('','---------'), ('M','Male'), ('F','Female'), ('U','unknown')),
            required=False,
            help_text='Not Implemented')
    visa_held = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter,
            help_text='Not Implemented')
#    scholarship_from = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
#    scholarship_to = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
    scholarship_sem = forms.ModelChoiceField(Semester.objects.all(),
            label='Scholarship Semester Received',required=False,
            help_text='Not Implemented')
