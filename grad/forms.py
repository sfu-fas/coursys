from django.forms.models import ModelForm
from django.forms import forms
from grad.models import Supervisor, GradProgram, GradStudent, GradStatus,\
    GradRequirement
from coredata.models import Member

class SupervisorForm(ModelForm):
    def clean(self):
        data = self.cleaned_data
        if 'supervisor' in data:
            if data['external']:
                raise forms.ValidationError("Please enter only one of Supervisor or an External supervisor.")
        else:
            if not data['external']:
                raise forms.ValidationError("Please have at least one of Supervisor or an External supervisor.")
        return data
    
    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'position', 'created_by', 'modified_by' )
        
class PotentialSupervisorForm(ModelForm): 
    class Meta:
        model = Supervisor
        exclude = ('student', 'is_potential', 'is_senior', 'position', 'created_by', 'modified_by', 'external' )


def possible_supervisors(unit):
    """
    .choices list of people who might supervise grad students in this unit
    
    Selects instructors and previous supervisors in that unit (who still have
    active computing accounts)
    """
    # instructors of courses in the unit
    people = set(m.person for m in
             Member.objects.filter(role="INST", offering__owner=unit)
             .exclude(offering__component="SEC") if m.person.userid)
    # previous supervisors
    people |= set(s.supervisor for s in
              Supervisor.objects.filter(student__program__unit=unit) 
              if s.supervisor and s.supervisor.userid)
    
    people = list(people)
    people.sort()
    return [(p.id, p.name()) for p in people]

class GradAcademicForm(ModelForm):
    class Meta: 
        model = GradStudent
        fields = ('research_area', 'campus', 'english_fluency', 'mother_tongue', 'is_canadian', 'passport_issued_by', 'special_arrangements', 'comments')

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

