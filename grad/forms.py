from django.forms.models import ModelForm
from django import forms
from django.db.models import Q
from django.db.models.query import QuerySet
import grad.models as gradmodels
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus, GradProgramHistory, \
    GradRequirement, CompletedRequirement, LetterTemplate, Letter, Promise, Scholarship, \
    ScholarshipType, SavedSearch, OtherFunding, GradFlagValue, FinancialComment, GRAD_CAMPUS_CHOICES, \
    THESIS_TYPE_CHOICES, THESIS_OUTCOME_CHOICES
from courselib.forms import StaffSemesterField
from coredata.models import Person, Semester, Role, VISA_STATUSES
from django.forms.models import BaseModelFormSet
#from django.core.exceptions import ValidationError
from django.forms.widgets import HiddenInput
from django.template import Template, TemplateSyntaxError
from itertools import ifilter, chain
import unicodecsv as csv
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.core.validators import EMPTY_VALUES
from advisornotes.forms import StudentSearchForm

class QuickSearchForm(StudentSearchForm):
    pass
#    incl_active = forms.BooleanField(initial=True)
#    incl_appl = forms.BooleanField(initial=True)
#    incl_grad = forms.BooleanField(initial=False)
#   incl_oldappl = forms.BooleanField(initial=False)

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
        if person_id in choices and person_id != -1:
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
    supervisor = SupervisorField(required=False, label="Committee Member")
    
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
                pass
                #print "No supervisor data has been passed. Treat form as empty"
                raise forms.ValidationError("Please have at least one of Supervisor or an External supervisor.")
        return data
    
    def has_changed(self):
        "Force update even if it doesn't look like anything changed (since view code does fiddle with object)"
        return True
    
    class Meta:
        model = Supervisor
        exclude = ('student', 'created_by', 'modified_by', 'removed', 'config', 'position')
        
class PotentialSupervisorForm(ModelForm): 
    def set_supervisor_choices(self, choices):
        self.fields['supervisor'].choices = choices
    
    class Meta:
        model = Supervisor
        exclude = ('student', 'supervisor_type', 'position', 'created_by', 'modified_by', 'external', 'removed', 'config')

def possible_supervisor_people(units):
    roles = Role.objects.filter(unit__in=units, role__in=['FAC', 'SUPV']).select_related('person')
    return set(r.person for r in roles)
    # instructors of courses in the unit
    #people = set(m.person for m in
    #         Member.objects.filter(role="INST", offering__owner__in=units).select_related('person')
    #         .exclude(offering__component="SEC") if m.person.userid)
    # previous supervisors
    #people |= set(s.supervisor for s in
    #          Supervisor.objects.filter(student__program__unit__in=units).select_related('supervisor') 
    #          if s.supervisor and s.supervisor.userid)
    #return people
    
def possible_supervisors(units, extras=[], null=False):
    """
    .choices list of people who might supervise grad students in these units.
    Extras to indicate values you know about (e.g. the current value(s))
    
    Selects instructors in those units (who still have active computing accounts)
    """
    people = possible_supervisor_people(units)
    people |= set(extras)
    people = list(people)
    people.sort()
    supervisors = [(p.id, p.name()) for p in people]
    if null:
        return [(-1, u'\u2014')] + supervisors
    else:
        return supervisors

class BaseSupervisorsFormSet(BaseModelFormSet):
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
    sin = forms.CharField( label = 'SIN', help_text='Social Insurance Number', required=False )
    place_of_birth = forms.CharField(required=False)
    bachelors_cgpa = forms.CharField(required=False)
    masters_cgpa = forms.CharField(required=False)
    progress = forms.CharField(required=False)
    qualifying_exam_date = forms.DateField(required=False)
    qualifying_exam_location = forms.CharField(required=False)

    class Meta: 
        model = GradStudent
        fields = ('research_area', 'campus', 'english_fluency', 'mother_tongue', 'is_canadian', 'passport_issued_by', 'comments') 
        widgets = {
                   'research_area': forms.Textarea(attrs={'rows': 3, 'cols': 40}),
                   }

class GradProgramHistoryForm(ModelForm):
    start_semester = StaffSemesterField()
    class Meta: 
        model = GradProgramHistory
        fields = ('program', 'start_semester', 'starting')
        widgets = {
                   'research_area': forms.Textarea(attrs={'rows': 3, 'cols': 40}),
                   }

class GradProgramForm(ModelForm):
    class Meta:
        model = GradProgram
        exclude = ('created_by', 'modified_by', 'hidden')
        
class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
        exclude = ('created_by', 'modified_by' )

class GradStatusForm(ModelForm):
    start = StaffSemesterField(label="Effective Semester",
            help_text="Semester when this status is effective")
    
    def clean_end(self):
        en = self.cleaned_data.get('end', None)
        st = self.cleaned_data.get('start', None)
        if not en or not st:
            return None
        if st > en:
            raise forms.ValidationError("Status cannot end before it begins")
        return en
        
    class Meta:
        model = GradStatus
        exclude = ('student', 'created_by', 'hidden', 'end', 'start_date')
        hidden = ('id')
        widgets = {
                   'notes': forms.Textarea(attrs={'rows': 2, 'cols': 40}),
                   }

class GradRequirementForm(ModelForm):
    class Meta:
        model = GradRequirement
        exclude = ('hidden','series')

class LetterTemplateForm(ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'35', 'cols': '60'}))
    class Meta:
        model = LetterTemplate
        exclude = ('created_by',)
    
    def clean_content(self):
        content = self.cleaned_data['content']
        try:
            Template(content)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
        return content

class LetterForm(ModelForm):
    use_sig = forms.BooleanField(initial=True, required=False, label="Use signature",
                                 help_text='Use the "From" person\'s signature, if on file?')    
    class Meta: 
        model = Letter
        exclude = ('created_by', 'config', 'template')
        widgets = {
                   'student': forms.HiddenInput(),
                   'to_lines': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
                   'from_lines': forms.Textarea(attrs={'rows': 3, 'cols': 30}),
                   'content': forms.Textarea(attrs={'rows':'25', 'cols': '70'}),
                   }
    
    def __init__(self, *args, **kwargs):
        super(LetterForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            self.initial['use_sig'] = kwargs['instance'].use_sig()
    
    def clean_use_sig(self):
        use_sig = self.cleaned_data['use_sig']
        self.instance.config['use_sig'] = use_sig
        return use_sig

class CompletedRequirementForm(ModelForm):
    semester = StaffSemesterField()
    class Meta:
        model = CompletedRequirement
        exclude = ('removed', 'student')


class PromiseForm(ModelForm):
    start_semester = StaffSemesterField()
    end_semester = StaffSemesterField()
    
    def clean_end_semester(self):
        en = self.cleaned_data.get('end_semester', None)
        st = self.cleaned_data.get('start_semester', None)
        if not en or not st:
            return None
        if st > en:
            raise forms.ValidationError("Promise cannot end before it begins")
        return en

    class Meta:
        model = Promise
        exclude = ('student','removed')
      
class ScholarshipForm(ModelForm):
    start_semester = StaffSemesterField()
    end_semester = StaffSemesterField()
    class Meta:
        model = Scholarship
        exclude = ('student','removed')

class OtherFundingForm(ModelForm):
    semester = StaffSemesterField()
    class Meta:
        model = OtherFunding
        exclude = ('student', 'removed')

class FinancialCommentForm(ModelForm):
    semester = StaffSemesterField()
    class Meta:
        model = FinancialComment
        exclude = ('student', 'removed', 'created_at', 'created_by')

class GradFlagValueForm(ModelForm):
    class Meta:
        model = GradFlagValue
        exclude = ('student','flag')

                
class new_scholarshipTypeForm(ModelForm):
    class Meta:
        model = ScholarshipType
        exclude = ('hidden',)

class GradDefenceForm(forms.Form):
    thesis_type = forms.ChoiceField(choices=THESIS_TYPE_CHOICES,
                                    required=True, label='Work type')
    work_title = forms.CharField(help_text='Title of the Thesis/Project/Extended Essay', max_length=300,
                                 widget=forms.TextInput(attrs={'size': 70}))
    exam_date = forms.DateField(required=False, help_text="Date of the Examination")
    thesis_location = forms.CharField(help_text="Location of the Examination", max_length=300, label='Location', 
                                required=False,
                                widget=forms.TextInput(attrs={'size':55}))
    
    chair = SupervisorField(required=False, label="Defence chair")
    internal = SupervisorField(required=False, label="SFU examiner")
    external = forms.CharField(max_length=200, required=False, label="External examiner",
                               help_text='Name of the external examiner')
    external_email = forms.EmailField(required=False, label="External email",
                                      help_text='Email address of the external examiner')
    external_contact = forms.CharField(required=False, label="External contact",
                                       help_text='Contact information for the external examiner',
                                       widget=forms.Textarea(attrs={'rows': 4, 'cols': 40}))
    external_attend = forms.ChoiceField(choices=[('','Unknown'), ('P','In-person'), ('A','in abstentia'), ('T','By teleconference')],
                                    required=False, label='External Attending')
    
    thesis_outcome = forms.ChoiceField(choices=THESIS_OUTCOME_CHOICES, required=False, label="Outcome")

    def set_supervisor_choices(self, choices):
        """
        Set choices for the supervisor
        """
        self.fields['chair'].fields[0].choices = [("","Other")] + choices
        self.fields['chair'].widget.widgets[0].choices = [("","Other")] + choices
        self.fields['internal'].fields[0].choices = [("","Other")] + choices
        self.fields['internal'].widget.widgets[0].choices = [("","Other")] + choices

class GradSemesterForm(forms.Form):
    start_semester = StaffSemesterField(required=False)
    end_semester = StaffSemesterField(required=False)
    # I'm commenting the following out because I suspect it will cause confusion. All the guts are there to make it work if needed, though.
    #ignore = forms.BooleanField(initial=False, required=False,
    #                            help_text="Ignore the values here and revert to the default values based on the student's statuses.")



# creates an 'atom' to represent 'Unknown' (but it's not None) 
Unknown = type('Unknown', (object,), {'__repr__':lambda self:'Unknown'})()

class NullBooleanSearchSelect(forms.widgets.Select):
    """
    A Select Widget intended to be used with NullBooleanSearchField.
    """
    def __init__(self, attrs=None):
        choices = ((u'', '---------'), (u'2', u'Yes'), (u'3', u'No'), (u'1', u'Unknown'))
        super(NullBooleanSearchSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {Unknown: u'1', True: u'2', False: u'3', u'1':u'1', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u''
        return super(NullBooleanSearchSelect, self).render(name, value, attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        return {u'1': Unknown,
                Unknown: Unknown,
                'Unknown': Unknown,
                u'2': True,
                True: True,
                'True': True,
                u'3': False,
                'False': False,
                False: False}.get(value, None)

    def _has_changed(self, initial, data):
        # For a NullBooleanSearchSelect, None (empty), Unknown (unknown) 
        # and False (No) are not the same
        if initial is not None and initial is not Unknown:
            initial = bool(initial)
        if data is not None and data is not Unknown:
            data = bool(data)
        return initial != data

class NullBooleanSearchField(forms.NullBooleanField):
    """
    A field whose valid values are Empty, None, True and False. Invalid values are
    cleaned to Empty.
    """
    widget = NullBooleanSearchSelect

    def to_python(self, value):
        if value in (True, 'True', '1'):
            return True
        elif value in (False, 'False', '0'):
            return False
        elif value in (Unknown, 'Unknown', '-1'):
            return Unknown
        else:
            return ''

    validate = forms.BooleanField.validate

COLUMN_CHOICES = (
        # first field is interpreted by getattribute template filter (grad/templatetags/getattribute.py)
        ('person.last_name',        'Last Name'),
        ('person.first_name',       'First Name'),
        ('person.pref_first_name',  'Pref First Name'),
        ('person.middle_name',      'Middle Name'),
        ('person.emplid',           'Employee ID'),
        ('person.userid',           'User ID'),
        ('email',                   'Email Address'),
        ('appemail',                'Application Email'),
        ('program',                 'Program'),
        ('research_area',           'Research Area'),
        ('campus',                  'Campus'),
        ('start_semester',          'Start Sem'),
        ('end_semester',            'End Sem'),
        ('current_status',          'Current Status'),
        ('active_semesters',        'Active Semesters'),
        ('senior_supervisors',      'Supervisor(s)'),
        ('supervisors',             'Committee Members'),
        ('completed_req',           'Completed Req'),
        ('gpa',                     'CGPA'),
        ('visa',                    'Visa'),
        ('gender',                  'Gender'),
        ('scholarships',            'Scholarships'),
        ('unit',                    'Unit'),
        )
COLUMN_WIDTHS_DATA = (
        # column widths for Excel export
        # units seem to be ~1/100 mm
        ('person.emplid',           3000),
        ('person.userid',           2800),
        ('person.first_name',       5000),
        ('person.middle_name',      5000),
        ('person.last_name',        6000),
        ('person.pref_first_name',  4000),
        ('email',                   5000),
        ('appemail',                5000),
        ('program',                 3000),
        ('research_area',           6000),
        ('campus',                  3000),
        ('start_semester',          3000),
        ('end_semester',            3000),
        ('current_status',          3000),
        ('active_semesters',        2000),
        ('senior_supervisors',      6000),
        ('supervisors',             9000),
        ('completed_req',           10000),
        ('gpa',                     2000),
        ('visa',                    3000),
        ('gender',                  2000),
        ('scholarships',            10000),
        ('unit',                    3000),
        )
COLUMN_WIDTHS = dict(COLUMN_WIDTHS_DATA)

def _is_not_empty(v):
    """
    Finds not-specified values from search form
    """
    if isinstance(v, QuerySet):
        return v.count() > 0
    else:
        return v not in EMPTY_VALUES


class SearchForm(forms.Form):
    
    first_name_contains = forms.CharField( required=False )
    last_name_contains = forms.CharField( required=False )

    start_semester_start = StaffSemesterField(required=False, label="Start semester after")
    start_semester_end = StaffSemesterField(required=False,
            help_text='Semester in which the student started their program', label="Start semester before")
    end_semester_start = StaffSemesterField(required=False, label="End semester after")
    end_semester_end = StaffSemesterField(required=False, label="End semester before",
            help_text='Semester in which the student completed/left their program')
    
    student_status = forms.MultipleChoiceField(gradmodels.STATUS_CHOICES,
            required=False, help_text="Student's current status"
            )
    
    program = forms.ModelMultipleChoiceField(GradProgram.objects.all(), required=False)
    grad_flags = forms.MultipleChoiceField(choices=[],
            label='Program Options', required=False)
    campus = forms.MultipleChoiceField(GRAD_CAMPUS_CHOICES, required=False)
    supervisor = forms.MultipleChoiceField([], required=False, label='Senior Supervisor')
    
    requirements = forms.MultipleChoiceField(choices=[],
            label='Completed requirements', required=False)
    requirements_st = forms.ChoiceField((
            ('AND',mark_safe(u'Student must have completed <em>all</em> of these requirements')),
            ('OR',mark_safe(u'Student must have completed <em>any</em> of these requirements'))),
            label='Requirements search type', required=False, initial='AND',
            widget=forms.RadioSelect)
    incomplete_requirements = forms.MultipleChoiceField([],
            label='Incomplete requirements', required=False)

    is_canadian = NullBooleanSearchField(required=False)
    
    financial_support = forms.MultipleChoiceField((
            ('N','None'),
            ('S','Scholarship'),
            ('O','Other Funding'),
            ('P','Promise')
            ),required=False)
    
    gpa_min = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gpa_max = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gender = forms.ChoiceField((('','---------'), ('M','Male'), ('F','Female'), ('U','Unknown')),
            required=False)
    visa = forms.MultipleChoiceField(VISA_STATUSES, required=False,)
    scholarship_sem = forms.ModelMultipleChoiceField(Semester.objects.all(),
            label='Scholarship Semester Received',required=False)
    scholarshiptype = forms.ModelMultipleChoiceField(ScholarshipType.objects.all(),
            label='Received Scholarship', required=False)

    columns = forms.MultipleChoiceField(COLUMN_CHOICES, initial=('person.last_name', 'person.first_name', 'person.emplid', 'person.userid', 'program', 'current_status', ),
            help_text='Columns to display in the search results.')

    sort = forms.CharField(required=False, widget=forms.HiddenInput()) # used to persist table sorting across "modify search" workflow
    
    semester_range_fields = [
            'start_semester_start',
            'start_semester_end',
            'end_semester_start',
            'end_semester_end',
            ]
    personal_fields = [
            'first_name_contains',
            'last_name_contains',
            'is_canadian',
            'gender',
            'visa',            
            'gpa_min',
            'gpa_max'
            ]
    program_fields = [
            'program',
            'grad_flags',
            'campus',
            'supervisor',
            ]
    requirement_fields = [
            'requirements',
            'requirements_st',
            'incomplete_requirements',
            ]
    
    status_fields = [
            'student_status',
            ]
                      
    financial_fields = [
            'financial_support',
            'scholarship_sem',
            'scholarshiptype',
            ]

    col_fields = [
            'columns', 'sort']
    
    def clean_requirements_st(self):
        value = self.cleaned_data['requirements_st']
        if not value and len(self.cleaned_data['requirements']) > 1:
            raise ValidationError, u"Specify a search type for requirements"
        return value
    
    def clean_financial_support(self):
        value = self.cleaned_data['financial_support']
        if 'N' in value and len(value) > 1:
            raise ValidationError, u"If 'None' is selected, nothing else can be selected"
        return value
    
    def _make_query(self, query_string, query_param=None):
        query_value = self.cleaned_data.get(query_string, None)
        if _is_not_empty(query_value):
            if query_param is None:
                query_param = query_string
            if query_value is Unknown:
                query_value = None
            return Q(**{query_param:query_value})
        return None
    
    def get_query(self):
        if not self.is_valid():
            raise Exception, "The form needs to be valid to get the search query"
        auto_queries = [
                #('start_semester_start', 'start_semester__gte'),
                #('start_semester_end', 'start_semester__lte'),
                #('end_semester_start', 'end_semester__gte'),
                #('end_semester_end', 'end_semester__lte'),
                ('first_name_contains', 'person__first_name__icontains' ),
                ('last_name_contains', 'person__last_name__icontains' ),
                ('student_status', 'current_status__in'),
                ('application_status', 'application_status__in'),
                ('program','program__in'),
#                ('requirements','completedrequirement__requirement__in'),
                ('is_canadian',),
                ('campus','campus__in'),
                ('scholarship_sem', 'scholarship__start_semester__in'),
                ('scholarshiptype', 'scholarship__scholarship_type__in'),
                ]
        manual_queries = []
        
        if self.cleaned_data.get('start_semester_start', None) is not None:
            manual_queries.append( Q(start_semester__name__gte=self.cleaned_data['start_semester_start'].name) )
        if self.cleaned_data.get('start_semester_end', None) is not None:
            manual_queries.append( Q(start_semester__name__lte=self.cleaned_data['start_semester_end'].name) )
        if self.cleaned_data.get('end_semester_start', None) is not None:
            manual_queries.append( Q(end_semester__name__gte=self.cleaned_data['end_semester_start'].name) )
        if self.cleaned_data.get('end_semester_end', None) is not None:
            manual_queries.append( Q(end_semester__name__lte=self.cleaned_data['end_semester_end'].name) )

        if self.cleaned_data.get('supervisor', None):
            person_ids = self.cleaned_data['supervisor']
            supervisors = Supervisor.objects.filter(supervisor__in=person_ids, supervisor_type='SEN', removed=False)
            student_ids = [s.student_id for s in supervisors]
            manual_queries.append( Q(id__in=student_ids) )

        if self.cleaned_data.get('grad_flags', None):
            flag_ids = self.cleaned_data['grad_flags']
            gradflagvalues = GradFlagValue.objects.filter(flag__id__in=flag_ids, value=True)
            student_ids = [gfv.student.id for gfv in gradflagvalues] 
            manual_queries.append( Q(id__in=student_ids) )
        
        if self.cleaned_data.get('financial_support', None) is not None:
            if 'S' in self.cleaned_data['financial_support']:
                manual_queries.append(Q(scholarship__amount__gt=0))
            if 'O' in self.cleaned_data['financial_support']:
                manual_queries.append(Q(otherfunding__amount__gt=0))
            if 'P' in self.cleaned_data['financial_support']:
                manual_queries.append(Q(promise__amount__gt=0))
            if 'N' in self.cleaned_data['financial_support']:
                manual_queries.append(
                        ~Q(pk__in=gradmodels.Scholarship.objects.all().values('student')) &
                        ~Q(pk__in=gradmodels.OtherFunding.objects.all().values('student')) &
                        ~Q(pk__in=gradmodels.Promise.objects.all().values('student')))

        if self.cleaned_data.get('incomplete_requirements', False):
            # If a student has ANY of these requirements he will be included.
            inc_req = self.cleaned_data['incomplete_requirements']
            completed_req = CompletedRequirement.objects.filter(requirement__series__in=inc_req)
            completed_req_students = set(cr['student_id'] for cr in completed_req.values('student_id'))
            manual_queries.append(~Q(pk__in=completed_req_students))
                    
        if self.cleaned_data.get('requirements', False):
            if self.cleaned_data['requirements_st'] == 'OR':
                # completed OR
                auto_queries.append(('requirements', 'completedrequirement__requirement__series__in'))
            else:
                # completed AND
                for series in self.cleaned_data['requirements']:
                    manual_queries.append(
                            Q(pk__in=
                              CompletedRequirement.objects.filter(requirement__series=series).values('student_id')
                              )
                            )
            
        # passes all of the tuples in auto_queries to _make_query as arguments
        # (which returns a single Q object) and then reduces the auto_queries
        # and manual_queries into one Q object using the & operator
        query = reduce(Q.__and__, 
                    chain(ifilter(lambda x:x is not None, 
                        (self._make_query(*qargs) for qargs in auto_queries)),
                        manual_queries),
                    Q())
        #print self.cleaned_data
        return query#, exclude_query
    
    def _secondary_filter(self, gradstudent):
        return ((gradstudent.person.gender() == self.cleaned_data['gender']
                if _is_not_empty(self.cleaned_data.get('gender', None))
                else True) and
                
                (gradstudent.person.gpa() >= self.cleaned_data['gpa_min']
                if _is_not_empty(self.cleaned_data.get('gpa_min', None))
                else True) and
                
                (gradstudent.person.gpa() <= self.cleaned_data['gpa_max']
                if _is_not_empty(self.cleaned_data.get('gpa_max', None))
                else True)
#                and
#                ((gradstudent.person.config['citizen'].lower() == 'canadian') ==
#                self.cleaned_data['is_canadian']
#                if _is_not_empty(self.cleaned_data.get('is_canadian', None))
#                else True)
                and
                (gradstudent.person.visa() in self.cleaned_data['visa']
                if _is_not_empty(self.cleaned_data.get('visa', None))
                else True)
                )
    
    def secondary_filter(self):
        # this returns a function in case it needs to use a closure
        # to cache some data used in the filter
        return self._secondary_filter

    def search_results(self, units):
        query = self.get_query()
        grads = GradStudent.objects.filter(program__unit__in=units).filter(query).select_related('person', 'program').distinct()
        return filter(self.secondary_filter(), grads)


class SaveSearchForm(ModelForm):
    class Meta:
        model = SavedSearch
        exclude = ('config',)
        widgets = {
            'person': HiddenInput(),
            'query': HiddenInput(),
        }
    name = forms.CharField(label="Save Search As:")
    
    def __init__(self, *args, **kwargs):
        super(SaveSearchForm, self).__init__(*args, **kwargs)
        self.initial['name'] = self.instance.name()
    
    #def clean(self):
    #    super(SaveSearchForm, self).clean()
    #    if self.cleaned_data['person'] != self.instance.person:
    #        raise ValidationError('Person for saved search must be current user')
    #    return self.cleaned_data
    
    def save(self, *args, **kwargs):
        self.instance.set_name(self.cleaned_data['name'])
        return super(SaveSearchForm, self).save(*args, **kwargs)

class UploadApplicantsForm(forms.Form):
    csvfile = forms.FileField(required=True, label="PCS data export")
    unit = forms.ChoiceField(choices=[], help_text="The unit students are being imported for")
    semester = forms.ChoiceField(choices=[], help_text="The start semester for these students")
    
    def clean_csvfile(self):        
        csvfile = self.cleaned_data['csvfile']
        if csvfile != None and (not csvfile.name.endswith('.csv')) and\
           (not csvfile.name.endswith('.CSV')):
            raise forms.ValidationError(u"Only .csv files are permitted")
        
        return csvfile
    

PCS_COLUMNS = [ # (key, header)
               ('appid', 'ID'),
               ('emplid', 'Application ID'),
               ('email', 'Contact Email'),
               ('dob', 'Date of Birth'),
               ('program', 'Program of Study'),
               ('lastup', 'Last Update'),
               ('resarea', 'Primary Research Area'),
               ('firstlang', 'First Language'),
               ('complete', 'Confirmation of Completion of Application'),
               ('decision', 'Decision'),
               ('notes', 'Notes'),
               ('potsuper', 'S1 name'), # TODO: is that right?
               ]

PCS_COL_LOOKUP = dict(((hdr, key) for key,hdr in PCS_COLUMNS))
PCS_HDR_LOOKUP = dict(PCS_COLUMNS)

from django.db import transaction
from coredata.models import Unit
from coredata.queries import add_person, SIMSProblem, grad_student_info
from log.models import LogEntry
import datetime, StringIO

@transaction.atomic
def process_pcs_row(row, column, rownum, unit, semester, user):
    """
    Process a single row from the PCS import
    """
    appsemester = semester.previous_semester()
    warnings = []
    ident = "in row %i" % (rownum)
    appid = row[column['appid']]
    emplid = row[column['emplid']]
    program = row[column['program']]

    # get Person, from SIMS if necessary
    try:
        p = Person.objects.get(emplid=int(emplid))
    except ValueError:
        warnings.append("Bad emplid %s: not processing that row." % (ident))
        return warnings
    except Person.DoesNotExist:
        try:
            p = add_person(emplid)
        except SIMSProblem as e:
            return e.message

    ident = 'for "%s"' % (p.name())

    # update information on the Person
    email = row[column['email']]
    if email: p.config['applic_email'] = email

    dob = row[column['dob']]
    if dob:
        try:
            dt = datetime.datetime.strptime(dob, "%Y-%m-%d")
            p.config['birthdate'] = dt.date().isoformat()
        except ValueError:
            warnings.append("Bad birthdate %s." % (ident))
    
    # get extended SIMS data
    data = grad_student_info(emplid)
    p.config.update(data)
    
    p.save()
    
    #print "Importing %s" % (p)
    
    # get GradStudent, creating if necessary
    
    # a unique identifier for this application, so we can detect repeated imports (and handle gracefully)
    uid = "%s-%s-%s-%s" % (unit.slug, semester.name, appid, emplid)
    # TODO: wrong, wrong, wrong. Figure out how to select program from import data
    program = GradProgram.objects.filter(unit=unit)[0]

    # find the old GradStudent if possible
    gss = GradStudent.objects.filter(program__unit=unit, person=p)
    gs = None
    for g in gss:
        if 'app_id' in g.config and g.config['app_id'] == uid:
            gs = g
            break
    if not gs:
        gs = GradStudent(program=program, person=p)
        gs.config['app_id'] = uid
    
    resarea = row[column['resarea']]
    firstlang = row[column['firstlang']]
    
    gs.research_area = resarea
    gs.mother_tongue = firstlang
    gs.created_by = user.userid
    gs.updated_by = user.userid
    gs.config['start_semester'] = semester.name
    gs.save()
    
    complete = row[column['complete']].strip()
    decision = row[column['decision']].strip()
    notes = row[column['notes']].strip()
    gs.config['decisionnotes'] = notes
    
    old_st = GradStatus.objects.filter(student=gs, start__name__gte=semester.name)
    if not old_st:
        # if no old status for current semester, create one
        
        # application completion status
        if complete == 'AppConfirm':
            st = GradStatus(student=gs, status="COMP", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif complete == '':
            st = GradStatus(student=gs, status="INCO", start=appsemester, end=None, notes="PCS import")
            st.save()
        else:
            warnings.append('Unknown "Confirmation of Completion of Application" value %s.' % (ident))
        
        # decision status
        if decision == 'DECL':
            st = GradStatus(student=gs, status="DECL", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif decision == '':
            st = GradStatus(student=gs, status="OFFO", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif decision == 'R':
            st = GradStatus(student=gs, status="REJE", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif decision == 'HOLD':
            st = GradStatus(student=gs, status="HOLD", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif decision == 'AMScT':
            # TODO: bump program to MSc thesis
            st = GradStatus(student=gs, status="CONF", start=appsemester, end=None, notes="PCS import")
            st.save()
        elif decision == 'AMScC':
            # TODO: bump program to MSc course-based
            st = GradStatus(student=gs, status="CONF", start=appsemester, end=None, notes="PCS import")
            st.save()


    # potential supervisor
    potsuper = row[column['potsuper']]
    if potsuper:
        superv = None
        external = None
        try:
            ps_last, ps_first = potsuper.split(', ')
        except ValueError:
            warnings.append('Bad potential supervisor name %s: will store them as an "external" supervisor.' % (ident))
            external = potsuper
        else:
            potentials = possible_supervisor_people([unit])
            potential_ids = [p.id for p in potentials]
            query = Q(last_name=ps_last, first_name=ps_first) | Q(last_name=ps_last, pref_first_name=ps_first)
            people = Person.objects.filter(query, id__in=potential_ids)
            if people.count() == 1:
                superv = people[0]
            else:
                warnings.append('Coundn\'t find potential supervisor %s: will store them as an "external" supervisor.' % (ident))
                external = potsuper

        old_s = Supervisor.objects.filter(student=gs, supervisor_type='POT')
        if old_s:
            s = old_s[0]
        else:
            s = Supervisor(student=gs, supervisor_type='POT')
        s.superv = superv
        s.external = external
        s.position = 0
        s.created_by = user.userid
        s.modified_by = user.userid
        s.save()
                
        
    l = LogEntry(userid=user.userid, description="Imported grad record for %s (%s) from PCS" % (p.name(), p.emplid), related_object=gs)
    l.save()
    
    return warnings

def process_pcs_export(csvdata, unit_id, semester_id, user):
    data = csv.reader(StringIO.StringIO(csvdata))
    unit = Unit.objects.get(id=unit_id)
    semester = Semester.objects.get(id=semester_id)
    warnings = []

    # find the columns by their heading, so we're tolerant of small changes to export format
    titles = data.next()
    column = {}
    req_columns = set(PCS_HDR_LOOKUP.keys())
    for i, header in enumerate(titles):
        if header in PCS_COL_LOOKUP:
            column[PCS_COL_LOOKUP[header]] = i
        #elif header.startswith('Application ('):
        #    column['name'] = i

    missing = req_columns - set(column.keys())
    if missing:
        return u"Missing columns in export: " + ', '.join([PCS_HDR_LOOKUP[key] for key in missing])
    
    # process data rows
    count = 0
    for i, row in enumerate(data):
        if len(row) == 0:
            continue

        w = process_pcs_row(row, column, i+2, unit, semester, user)
        warnings.extend(w)

        count += 1
    
    message = 'Imported information on %i students.\n' % (count)
    if warnings:
        message += '\nWarnings:\n'
        for w in warnings:
            message += '  ' + w + '\n'

    return message
        
