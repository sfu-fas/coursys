from django import forms
from discipline.models import DisciplineCase, DisciplineGroup
from coredata.models import Member

class DisciplineGroupForm(forms.ModelForm):
    students = forms.MultipleChoiceField(choices=[])
    
    def __init__(self, offering, *args, **kwargs):
        super(DisciplineGroupForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
    
    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']
    
    class Meta:
        model = DisciplineGroup
        widgets = {
            'offering': forms.HiddenInput(),
        }

class DisciplineCaseForm(forms.ModelForm):
    student = forms.ChoiceField(choices=[])

    def __init__(self, offering, *args, **kwargs):
        super(DisciplineCaseForm, self).__init__(*args, **kwargs)
        # store the course offering for validation
        self.offering = offering
    
    def clean_student(self):
        userid = self.cleaned_data['student']
        members = Member.objects.filter(offering=self.offering, person__userid=userid)
        if members.count() != 1:
            raise forms.ValidationError("Can't find student")

        return members[0]
    
    class Meta:
        model = DisciplineCase
        fields = ("student", "group")

class CaseIntroForm(forms.ModelForm):
    #intro = forms.CharField(widget=forms.Textarea)
    #intro = forms.CharField(required=False, label="Introductory sentence", widget=forms.TextInput(attrs={'size':'80'}))
    class Meta:
        model = DisciplineCase
        fields = ("intro",)
        widgets = {
            'intro': forms.TextInput(attrs={'size':'80'}),
        }


