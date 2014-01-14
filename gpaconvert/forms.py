from django import forms


class BaseGradeForm(forms.Form):
    name = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.grade_source = kwargs.pop('grade_source', None)
        super(BaseGradeForm, self).__init__(*args, **kwargs)
        self.initialize(self.grade_source)

    def clean_grade(self):
        grade = self.cleaned_data['grade']
        rule = self.grade_source.get_rule(grade)

        if rule:
            self.cleaned_data['rule'] = rule
            return grade
        else:
            raise forms.ValidationError('No rule found for grade')

    # Override these

    def initialize(self, grade_source):
        pass


class DiscreteGradeForm(BaseGradeForm):
    grade = forms.ChoiceField()

    def initialize(self, grade_source):
        values = grade_source.discrete_rules.values_list('lookup_value', flat=True)
        self.fields['grade'].choices = zip(values, values)


class ContinuousGradeForm(BaseGradeForm):
    grade = forms.DecimalField(max_digits=8, decimal_places=2)

    def initialize(self, grade_source):
        # TODO: Agree on min/max grade fields for GradeSource and limit the value of grade
        #       accordingly.
        pass
