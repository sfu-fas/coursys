from django import forms


class DiscreteGradeForm(forms.Form):
    name = forms.CharField()
    grade = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        grade_source = kwargs.pop('grade_source')
        super(DiscreteGradeForm, self).__init__(*args, **kwargs)
        self.initialize(grade_source)

    def initialize(self, grade_source):
        self.fields['grade'].choices = [(rule.id, rule.lookup_value)
                                        for rule in grade_source.discrete_rules.all()]
