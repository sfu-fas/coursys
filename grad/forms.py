from django.forms.models import ModelForm
from django import forms
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus,\
    GradRequirement, CompletedRequirement
from coredata.models import Member

class LabelTextInput(forms.TextInput):
    "TextInput with a bonus label"
    def __init__(self, label, *args, **kwargs):
        self.label = label
        super(LabelTextInput, self).__init__(*args, **kwargs)
    def render(self, *args, **kwargs):
        return " " + self.label + ": " + super(LabelTextInput, self).render(*args, **kwargs)

class SupervisorWidget(forms.MultiWidget):
    "Widget for entering salary/scholarship values"
    def __init__(self, *args, **kwargs):
        widgets = [forms.Select(), LabelTextInput(label=" or User ID", attrs={'size': 8, 'maxlength': 8})]
        kwargs['widgets'] = widgets
        super(SupervisorWidget, self).__init__(*args, **kwargs)
    
    def decompress(self, value):
        # should already be a list: if we get here, have no defaults
        return [0]*len([])

class SupervisorField(forms.MultiValueField):
    "Field for entering supervisor by either dropdown or userid"
    def __init__(self, *args, **kwargs):
        fields = [forms.ChoiceField(), forms.CharField(max_length=8)]
        kwargs['fields'] = fields
        kwargs['widget'] = SupervisorWidget()
        super(SupervisorField, self).__init__(*args, **kwargs)

    def compress(self, values):
        return values




class SupervisorForm(ModelForm):
    #supervisor = SupervisorField()
    
    def set_supervisor_choices(self, choices):
        self.fields['supervisor'].fields[0].choices = choices
        self.fields['supervisor'].widget.widgets[0].choices = choices

    def clean(self):
        data = self.cleaned_data
        if 'supervisor' in data:
            if data['external']:
                raise forms.ValidationError("Please enter only one of Supervisor or an External supervisor.")
        else:
            if not data['external']:
                raise forms.ValidationError("Please have at least one of Supervisor or an External supervisor.")
        return data
    
    def clean_supervisor(self):
        supervisor = self.cleaned_data['supervisor']
        return supervisor
    
    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'created_by', 'modified_by' )
        
class PotentialSupervisorForm(ModelForm): 
    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'position', 'created_by', 'modified_by', 'external' )


def possible_supervisors(units):
    """
    .choices list of people who might supervise grad students in these units
    
    Selects instructors and previous supervisors in those units (who still have
    active computing accounts)
    """
    # instructors of courses in the unit
    people = set(m.person for m in
             Member.objects.filter(role="INST", offering__owner__in=units).select_related('person')
             .exclude(offering__component="SEC") if m.person.userid)
    # previous supervisors
    people |= set(s.supervisor for s in
              Supervisor.objects.filter(student__program__unit__in=units).select_related('supervisor') 
              if s.supervisor and s.supervisor.userid)
    
    people = list(people)
    people.sort()
    return [(p.id, p.name()) for p in people]

def missing_requirements(grad):
    req = GradRequirement.objects.filter(program=grad.program)
    
    return req

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
        exclude = ('end', 'student', 'notes', 'created_by')
        
        
class GradRequirementForm(ModelForm):
    class Meta:
        model = GradRequirement

class CompletedRequirementForm(ModelForm):
    class Meta:
        model = CompletedRequirement
        fields = ('requirement', 'semester', 'date', 'notes')
