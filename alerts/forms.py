

class ProblemStatusForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ('status', 'resolved_until')
