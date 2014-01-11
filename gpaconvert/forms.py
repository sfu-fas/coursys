from django.forms.models import ModelForm
from django.forms.models import inlineformset_factory

from models import GradeSource
from models import DiscreteRule
from models import ContinuousRule

class GradeSourceForm(ModelForm):
    class Meta:
        model = GradeSource
        exclude = ("config",)


class DiscreteRuleForm(ModelForm):
    class Meta:
        model = DiscreteRule


class ContinuousRuleForm(ModelForm):
    class Meta:
        model = ContinuousRule


def rule_formset_factory(grade_source, reqpost=None):
    if grade_source.scale == 'DISC':
        DiscreteRuleFormSet = inlineformset_factory(GradeSource, DiscreteRule)
        formset = DiscreteRuleFormSet(reqpost, instance=grade_source)
    else:
        ContinuousRuleFormSet = inlineformset_factory(GradeSource, ContinuousRule)
        formset = ContinuousRuleFormSet(reqpost, instance=grade_source)

    return formset
