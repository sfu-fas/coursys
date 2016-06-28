from models import Asset
from django import forms
from coredata.models import Unit


class AssetForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        exclude = []
        model = Asset
        widgets = {
            'notes': forms.Textarea,
        }
