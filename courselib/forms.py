from django import forms
from coredata.models import Semester

class StaffSemesterField(forms.CharField):
    """
    A semester selection field that allows entering semester name (e.g. "1124") instead of selecting
    from a dropdown. More efficient for staff, who know those codes.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 4
        kwargs['widget'] = forms.TextInput(attrs={'size': '4'})
        super(StaffSemesterField, self).__init__(*args, **kwargs)
    
    def prepare_value(self, semester):
        "Convert to semester name for display in widget"
        if isinstance(semester, basestring):
            return semester
        if isinstance(semester, int):
            return "????" #TODO: Fix this. /grad/<xx>/manage_requirements breaks otherwise. 
        if isinstance(semester, Semester):
            return semester.name
        else:
            return ''

    def clean(self, val):
        "Convert semester name to semester object"
        if len(val.strip()) == 0:
            return None
        try:
            return Semester.objects.get(name=val)
        except Semester.DoesNotExist:
            raise forms.ValidationError, "Cannot find a semester with that label"
