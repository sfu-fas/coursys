from django.forms.models import ModelForm
from django import forms
from django.db.models import Q
import grad.models as gradmodels
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus,\
    GradRequirement, CompletedRequirement, LetterTemplate, Letter, Promise
from coredata.models import Person, Member, Semester, CAMPUS_CHOICES
from django.forms.formsets import BaseFormSet
from django.core.exceptions import ValidationError
from django.forms.widgets import NullBooleanSelect
from itertools import ifilter
import unicodecsv as csv

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
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'35', 'cols': '70'}))    
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

class new_promiseForm(ModelForm):
    class Meta:
        model = Promise
        exclude = ('student','comments')
      
        


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
    
    start_semester = forms.ModelMultipleChoiceField(Semester.objects.all(), required=False,
            help_text='Semester in which the Grad student has applied to start')
    end_semester = forms.ModelMultipleChoiceField(Semester.objects.all(), required=False)
    
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
    program = forms.ModelMultipleChoiceField(GradProgram.objects.all(), required=False)
#    degree = forms.ChoiceField(choices=(
#            ('','---------'),
#            ('INTL','International'),
#            ('CAN','Canadian')
#            ), required=False)
    requirements = forms.ModelMultipleChoiceField(GradRequirement.objects.all(), required=False,
            help_text='Not Implemented')
    is_canadian = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
    
    has_financial_support = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter,
            help_text='Not Implemented')
    campus = forms.MultipleChoiceField(CAMPUS_CHOICES, required=False,
            help_text='Uses "or", selecting nothing means any')
    gpa_min = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False)
    gpa_max = forms.DecimalField(max_value=4.33, min_value=0, decimal_places=2, required=False,
            help_text='Not Implemented')
    gender = forms.ChoiceField((('','---------'), ('M','Male'), ('F','Female'), ('U','unknown')),
            required=False)
    visa_held = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter,
            help_text='Not Implemented')
#    scholarship_from = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
#    scholarship_to = forms.NullBooleanField(required=False, widget=NullBooleanSelect_Filter)
    scholarship_sem = forms.ModelMultipleChoiceField(Semester.objects.all(),
            label='Scholarship Semester Received',required=False,
            help_text='Not Implemented')
    
    def _make_query(self, query_string, query_param=None):
        if query_string in self.cleaned_data and self.cleaned_data[query_string]:
            if query_param is None:
                query_param = query_string
            return Q(**{query_param:self.cleaned_data[query_string]})
        return None
    
    def get_query(self):
        if not self.is_valid():
            raise Exception, "The form needs to be valid to get the search query"
        queries = (
                ('start_semester', 'gradstatus__start__in'),
                ('end_semester', 'gradstatus__end__in'),
                ('student_status', 'gradstatus__status__in'),
                ('program','program__in'),
                ('is_canadian',),
                ('campus','campus__in'),
                )
        
        # passes all of the tuples in queries to _make_query as arguments
        # (which returns a single Q object) and then combines them (reduce)
        # into one Q object using the & operator
        query = reduce(Q.__and__, 
                    ifilter(lambda x:x is not None,
                        (self._make_query(*qargs) for qargs in queries)),
                    Q())
        
        # super complex stuff to get searching for gender to work nicely, because it's in a config field
        if 'gender' in self.cleaned_data and self.cleaned_data['gender']:
            gender_query = Q(person__config__icontains='"gender": "%s"' % self.cleaned_data['gender'])
            if self.cleaned_data['gender'] == 'U':
                gender_query |= ~Q(person__config__icontains='"gender":')
            query &= gender_query
            
        return query


from coredata.queries import add_person, SIMSProblem
import datetime
class UploadApplicantsForm(forms.Form):
    csvfile = forms.FileField(required=True, label="PCS data export")
    
    def clean_csvfile(self):        
        csvfile = self.cleaned_data['csvfile']
        if csvfile != None and (not csvfile.name.endswith('.csv')) and\
           (not csvfile.name.endswith('.CSV')):
            raise forms.ValidationError(u"Only .csv files are permitted")
        
        return self._process_pcs_export(csvfile)

    def _process_pcs_export(self, csvfile):
        data = csv.reader(csvfile)
        warnings = []

        # find the columsn by their heading, so we're tolerant of small changes to export format
        titles = data.next()
        column = {}
        req_columns = set(['emplid'])
        for i, header in enumerate(titles):
            if header == 'Application ID':
                column['emplid'] = i
            elif header == 'Contact Email':
                column['email'] = i
            #elif header.startswith('Application ('):
            #    column['name'] = i
            elif header == 'Date of Birth':
                column['dob'] = i
            #elif header == 'Gender':
            #    column['gender'] = i
            elif header == 'Citizenship':
                column['citizen'] = i
            #elif header == 'First Language':
            #    column['firstlang'] = i
            elif header == 'Program of Study':
                column['program'] = i
            elif header == 'Last Update':
                column['lastup'] = i

        missing = req_columns - set(column.keys())
        if missing:
            raise forms.ValidationError(u"Missing columns in export: " + ', '.join(missing))

        # process data rows
        for i, row in enumerate(data):
            if len(row) == 0:
                continue
            i += 2

            emplid = row[column['emplid']]
            email = row[column['email']]
            #name = row[column['name']]
            dob = row[column['dob']]
            #gender = row[column['gender']]
            citizen = row[column['citizen']]
            #firstlang = row[column['firstlang']]
            #program = row[column['program']]
            #lastup = row[column['lastup']]

            # get Person, from SIMS if necessary
            try:
                p = Person.objects.get(emplid=emplid)
            except Person.DoesNotExist:
                p = add_person(emplid)
            
            if isinstance(p, SIMSProblem):
                raise forms.ValidationError(u"Problem with reporting database: " + unicode(p))

            print p

            if email: p.config['applic_email'] = email
            if citizen: p.config['citizen'] = citizen

            if dob:
                try:
                    dt = datetime.datetime.strptime(dob, "%Y-%m-%d")
                    p.config['birthdate'] = dt.date().isoformat()
                except ValueError:
                    warnings.append("Bad birthdate in row %i." % (i))
            
            p.save()
        
        print warnings
        
