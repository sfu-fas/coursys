from django import forms
from .models import Visa, VisaDocumentAttachment
from coredata.widgets import CalendarWidget
from coredata.forms import PersonField
from coredata.models import Unit


class VisaForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(VisaForm, self).__init__(*args, **kwargs)
        #  The following two lines look stupid, but they are not.  request.units contains a set of units.
        #  in order to be used this way, we need an actual queryset.
        #
        #  In this case, we also include subunits.  If you manage visas for a parent unit, chances are you may be
        #  adding/removing them for people in your children units.
        unit_ids = [unit.id for unit in Unit.sub_units(request.units)]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    person = PersonField()

    class Meta:
        exclude = []
        model = Visa
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget
            }

    def clean(self):
        cleaned_data = super(VisaForm, self).clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if end_date is not None and start_date is not None and end_date < start_date:
            raise forms.ValidationError({'end_date': "End date cannot be before start date."})

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(VisaForm, self).is_valid(*args, **kwargs)


class VisaAttachmentForm(forms.ModelForm):
    class Meta:
        model = VisaDocumentAttachment
        exclude = ("visa", "created_by")
