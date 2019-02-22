from .models import Contact
from django import forms
from coredata.models import Unit


class ContactForm(forms.ModelForm):
    def __init__(self, request, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        #  The following two lines look stupid, but they are not.  request.units contains a set of units.
        #  in order to be used this way, we need an actual queryset.
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        self.fields['unit'].queryset = units
        self.fields['unit'].empty_label = None

    class Meta:
        model = Contact
        exclude = ['config', 'deleted']
        widgets = {
            'title': forms.TextInput(attrs={'size': 4}),
            'address': forms.Textarea
        }
