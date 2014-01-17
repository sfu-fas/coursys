from django import forms
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.forms.models import ModelForm
from django.forms.models import inlineformset_factory

from django_countries.countries import COUNTRIES

from gpaconvert.models import ContinuousRule
from gpaconvert.models import DiscreteRule
from gpaconvert.models import GradeSource


class GradeSourceListForm(forms.Form):
    country_choices =  (('', '--------'),) + tuple(COUNTRIES)
    country = forms.ChoiceField(choices=country_choices, required=False)


class GradeSourceForm(ModelForm):
    class Meta:
        model = GradeSource
        exclude = ("config",)


class GradeSourceChangeForm(ModelForm):
    class Meta:
        model = GradeSource
        exclude = ("config", "scale", "lower_bound", "upper_bound")


class DiscreteRuleForm(ModelForm):
    class Meta:
        model = DiscreteRule


class ContinuousRuleForm(ModelForm):
    class Meta:
        model = ContinuousRule


def rule_formset_factory(grade_source, reqpost=None):
    if grade_source.scale == 'DISC':
        DiscreteRuleFormSet = inlineformset_factory(GradeSource, DiscreteRule, can_delete=False)
        formset = DiscreteRuleFormSet(reqpost, instance=grade_source)
    else:
        ContinuousRuleFormSet = inlineformset_factory(GradeSource, ContinuousRule, can_delete=False)
        formset = ContinuousRuleFormSet(reqpost, instance=grade_source)

    return formset


class BaseGradeForm(forms.Form):
    name = forms.CharField()
    credits = forms.DecimalField(max_digits=5, decimal_places=2,
                                 validators=[MinValueValidator(0)])
    include_secondary_gpa = forms.BooleanField(required=False)

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
            self.cleaned_data['rule'] = None
            raise forms.ValidationError('No rule found for grade')

    # Override these

    def initialize(self, grade_source):
        pass


class DiscreteGradeForm(BaseGradeForm):
    grade = forms.ChoiceField()

    def initialize(self, grade_source):
        values = grade_source.discrete_rules.values_list('lookup_value', flat=True)
        self.fields['grade'].choices = [('', '----')] + zip(values, values)


class ContinuousGradeForm(BaseGradeForm):
    grade = forms.DecimalField(max_digits=8, decimal_places=2)

    def initialize(self, grade_source):
        self.fields['grade'].validators.extend([
            MinValueValidator(grade_source.lower_bound),
            MaxValueValidator(grade_source.upper_bound),
        ])
