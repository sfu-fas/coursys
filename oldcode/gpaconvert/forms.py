from django import forms
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.forms.models import ModelForm
from django.forms.models import inlineformset_factory

from django_countries import Countries
COUNTRIES = list(Countries())

from gpaconvert.models import ContinuousRule
from gpaconvert.models import DiscreteRule
from gpaconvert.models import GradeSource


class GradeSourceListForm(forms.Form):
    country_choices = [('', 'All Countries'),] + COUNTRIES
    country = forms.ChoiceField(choices=country_choices, required=False)

    def __init__(self, *args, **kwargs):
        f = super(GradeSourceListForm, self).__init__(*args, **kwargs)

        # limit country choices to those with some data
        used_countries = set(GradeSource.objects.active().order_by().values_list('country', flat=True).distinct())
        used_countries.add('') # the all-countries option
        choices = self.fields['country'].choices
        choices = [(k,v) for k,v in choices if k in used_countries]
        self.fields['country'].choices = choices

        return f



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
        exclude = []


class ContinuousRuleForm(ModelForm):
    class Meta:
        model = ContinuousRule
        exclude = []


def rule_formset_factory(grade_source, reqpost=None):
    if grade_source.scale == 'DISC':
        DiscreteRuleFormSet = inlineformset_factory(GradeSource, DiscreteRule, can_delete=True, extra=10)
        formset = DiscreteRuleFormSet(reqpost, instance=grade_source)
    else:
        ContinuousRuleFormSet = inlineformset_factory(GradeSource, ContinuousRule, can_delete=True, extra=10)
        formset = ContinuousRuleFormSet(reqpost, instance=grade_source)

    return formset


class BaseGradeForm(forms.Form):
    name = forms.CharField(required=False)
    credits = forms.DecimalField(max_digits=5, decimal_places=2,
                                 validators=[MinValueValidator(0)],
                                 widget=forms.NumberInput(attrs={'size': 3}))
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
        values = grade_source.all_discrete_grades()
        values = [v.lookup_value for v in values]
        self.fields['grade'].choices = [('', '\u2014')] + list(zip(values, values))


class ContinuousGradeForm(BaseGradeForm):
    grade = forms.DecimalField(max_digits=8, decimal_places=2)

    def initialize(self, grade_source):
        self.fields['grade'].validators.extend([
            MinValueValidator(grade_source.lower_bound),
            MaxValueValidator(grade_source.upper_bound),
        ])
        self.fields['grade'].widget.attrs['size'] = 5
