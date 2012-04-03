from django.forms.models import ModelForm
from django import forms
from django.db.models import Q
import grad.models as gradmodels
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus,\
    GradRequirement, CompletedRequirement, LetterTemplate, Letter, Promise, Scholarship,\
    ScholarshipType
from coredata.models import Person, Member, Semester, CAMPUS_CHOICES
from django.forms.formsets import BaseFormSet
#from django.core.exceptions import ValidationError
from django.forms.widgets import NullBooleanSelect
from django.template import Template, TemplateSyntaxError
from itertools import ifilter, chain
import unicodecsv as csv
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.core.validators import EMPTY_VALUES

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
        fields = ('program', 'research_area', 'campus', 'english_fluency', 'mother_tongue', 'is_canadian', 'passport_issued_by', 'special_arrangements', 'application_status', 'comments')

class GradProgramForm(ModelForm):
    class Meta:
        model = GradProgram
        exclude = ('created_by', 'modified_by' )        
        
class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
        exclude = ('created_by', 'modified_by' )
        
class GradStatusForm(ModelForm):
    def clean_end(self):
        en = self.cleaned_data['end']
        st = self.cleaned_data.get('start', None)
        if not en:
            return None
        if st > en:
            raise forms.ValidationError("Status cannot end before it begins")
        return en
        
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
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'35', 'cols': '70'}))    
    class Meta:
        model = LetterTemplate
        exclude = ('created_by')
    
    def clean_content(self):
        content = self.cleaned_data['content']
        try:
            Template(content)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
        return content

class LetterForm(ModelForm):
    class Meta: 
        model = Letter
        exclude = ('created_by', 'config')
        widgets = {
                   'student': forms.HiddenInput(),
                   'to_lines': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
                   'from_lines': forms.Textarea(attrs={'rows': 3, 'cols': 30}),
                   'content': forms.Textarea(attrs={'rows':'25', 'cols': '100'}),
                   }

class new_promiseForm(ModelForm):
    class Meta:
        model = Promise
        exclude = ('student','comments')
      
class new_scholarshipForm(ModelForm):
    class Meta:
        model = Scholarship
        exclude = ('student')
                
class new_scholarshipTypeForm(ModelForm):
    class Meta:
        model = ScholarshipType

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
        ('emplid', 'Employee ID'),
        ('userid', 'User ID'),
        ('firstn', 'First Name'),
        ('middle', 'Middle Name'),
        ('lastna', 'Last Name'),
        ('preffi', 'Preferred First Name'),
        # TODO Include stuff from config eg. email, phone, address
        ('progra', 'Program'),
        ('resear', 'Research Area'),
        ('campus', 'Campus'),
        )

class SearchForm(forms.Form):
    #TODO: finish
    
    start_semester_start = forms.ModelChoiceField(Semester.objects.all(), required=False)
    start_semester_end = forms.ModelChoiceField(Semester.objects.all(), required=False,
            help_text='Semester in which the Grad student has applied to start')
    end_semester_start = forms.ModelChoiceField(Semester.objects.all(), required=False)
    end_semester_end = forms.ModelChoiceField(Semester.objects.all(), required=False)
    
    # requirements?
    student_status = forms.MultipleChoiceField(gradmodels.STATUS_CHOICES,
#            widget=forms.CheckboxSelectMultiple,
            required=False,
            )
    application_status = forms.MultipleChoiceField(gradmodels.APPLICATION_STATUS_CHOICES, 
            required=False,
            )
    
    #program = forms.CharField(required=False)
    program = forms.ModelMultipleChoiceField(GradProgram.objects.all(), required=False)
#    degree = forms.ChoiceField(choices=(
#            ('','---------'),
#            ('INTL','International'),
#            ('CAN','Canadian')
#            ), required=False)
    requirements = forms.ModelMultipleChoiceField(GradRequirement.objects.all(),
            label='Completed requirements', required=False)
    requirements_st = forms.ChoiceField((
            ('AND',mark_safe(u'Student must have completed <em>all</em> of these requirements')),
            ('OR',mark_safe(u'Student must have completed <em>any</em> of these requirements'))),
            label='Requirements search type', required=False, 
            widget=forms.RadioSelect)
    is_canadian = NullBooleanSearchField(required=False)
    
    financial_support = forms.MultipleChoiceField((
            ('N','None'),
            ('S','Scholarship'),
            ('O','Other Funding'),
            ('P','Promise')
            ),required=False)
    
    campus = forms.MultipleChoiceField(CAMPUS_CHOICES, required=False,
            help_text='Uses "or", selecting nothing means any')
    gpa_min = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gpa_max = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gender = forms.ChoiceField((('','---------'), ('M','Male'), ('F','Female'), ('U','Unknown')),
            required=False)
    visa_held = NullBooleanSearchField(required=False, 
            help_text='Not Implemented, needs clarification on data in the database')
    scholarship_sem = forms.ModelMultipleChoiceField(Semester.objects.all(),
            label='Scholarship Semester Received',required=False)

    columns = forms.MultipleChoiceField(COLUMN_CHOICES, initial=('emplid', 'userid'),
            help_text='Columns to display in the search results.')
    
    semester_range_fields = [
            'start_semester_start',
            'start_semester_end',
            'end_semester_start',
            'end_semester_end',]
    
    regular_fields = [
            'student_status',
            'application_status',
            'program',
            'requirements',
            'requirements_st',
            'is_canadian',
            'financial_support',
            'campus',
            'gender',
            'visa_held',
            'scholarship_sem',]
#    regular_fields = ','.join(regular_fields)
    number_range_fields = [
            'gpa_min',
            'gpa_max']

    col_fields = [
            'columns']
    
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
        if query_value not in EMPTY_VALUES:
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
                # Possibly use __range=(start_date, end_date) ?
                ('start_semester_start', 'gradstatus__start__gte'),
                ('start_semester_end', 'gradstatus__start__lte'),
                ('end_semester_start', 'gradstatus__end__gte'),
                ('end_semester_end', 'gradstatus__end__lte'),
                ('student_status', 'gradstatus__status__in'),
                ('application_status',),
                ('program','program__in'),
#                ('requirements','completedrequirement__requirement__in'),
                ('is_canadian',),
                ('campus','campus__in'),
                ('scholarship_sem', 'scholarship__start_semester__in'),
                ]
        manual_queries = []
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
        
        if self.cleaned_data.get('requirements', False):
            if self.cleaned_data['requirements_st'] == 'OR':
                auto_queries.append(('requirements', 'completedrequirement__requirement__in'))
            else:
                manual_queries += [Q(pk__in=requirement.completedrequirement_set.all().values('student_id')) 
                        for requirement in self.cleaned_data['requirements']]
            
        # passes all of the tuples in auto_queries to _make_query as arguments
        # (which returns a single Q object) and then reduces the auto_queries
        # and manual_queries into one Q object using the & operator
        query = reduce(Q.__and__, 
                    chain(ifilter(lambda x:x is not None, 
                        (self._make_query(*qargs) for qargs in auto_queries)),
                        manual_queries),
                    Q())
        print self.cleaned_data
        return query#, exclude_query
    
    def _secondary_filter(self, gradstudent):
        return ((gradstudent.person.gender() == self.cleaned_data['gender']
                if self.cleaned_data.get('gender', None) not in EMPTY_VALUES
                else True) and
                
                (gradstudent.person.gpa() >= self.cleaned_data['gpa_min']
                if self.cleaned_data.get('gpa_min', None) not in EMPTY_VALUES
                else True) and
                
                (gradstudent.person.gpa() <= self.cleaned_data['gpa_max']
                if self.cleaned_data.get('gpa_max', None) not in EMPTY_VALUES
                else True))
    
    def secondary_filter(self):
        # this returns a function in case it needs to use a closure
        # to cache some data used in the filter
        return self._secondary_filter

class UploadApplicantsForm(forms.Form):
    csvfile = forms.FileField(required=True, label="PCS data export")
    unit = forms.ChoiceField(choices=[], help_text="The unit students are being imported for")
    semester = forms.ChoiceField(choices=[], help_text="The application semester")
    
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
               ]

PCS_COL_LOOKUP = dict(((hdr, key) for key,hdr in PCS_COLUMNS))
PCS_HDR_LOOKUP = dict(PCS_COLUMNS)

from coredata.models import Unit
from coredata.queries import add_person, SIMSProblem, grad_student_info
from log.models import LogEntry
import datetime, StringIO

def process_pcs_row(row, column, rownum, unit, semester, user):
    """
    Process a single row from the PCS import
    """
    warnings = []
    appid = row[column['appid']]
    emplid = row[column['emplid']]
    email = row[column['email']]
    #name = row[column['name']]
    dob = row[column['dob']]
    #gender = row[column['gender']]
    #citizen = row[column['citizen']]
    program = row[column['program']]

    # get Person, from SIMS if necessary
    try:
        p = Person.objects.get(emplid=emplid)
    except Person.DoesNotExist:
        try:
            p = add_person(emplid)
        except SIMSProblem as e:
            return e.message

    # update information on the Person
    if email: p.config['applic_email'] = email

    if dob:
        try:
            dt = datetime.datetime.strptime(dob, "%Y-%m-%d")
            p.config['birthdate'] = dt.date().isoformat()
        except ValueError:
            warnings.append("Bad birthdate in row %i." % (rownum))
    
    # get extended SIMS data
    data = grad_student_info(emplid)
    p.config.update(data)
    
    p.save()
    
    print "Importing %s" % (p)
    
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
    # TODO: gs.application_status
    gs.created_by = user.userid
    gs.updated_by = user.userid
    gs.save()
    
    # TODO: find more sensible status than "APPL" from SIMS?
    old_st = GradStatus.objects.filter(student=gs, start__name__gte=semester.name)
    if not old_st:
        # if no old status for current semester, create one
        st = GradStatus(student=gs, status="APPL", start=semester, end=None, notes="PCS import")
        st.save()
    
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
        
