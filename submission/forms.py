from django import forms
from submission.models import STATUS_CHOICES, TYPE_CHOICES
from django.forms.widgets import RadioSelect

class ComponentForm(forms.Form):
    title = forms.CharField(max_length=30, label='Title', help_text = 'Name for this component (e.g. "Part 1" or "Programming Section")')
    position = forms.IntegerField(min_value=0)

class ArchiveComponentForm(ComponentForm):
    max_size = forms.IntegerField(min_value=0, help_text = "Max size of the archive file")

class URLComponentForm(ComponentForm):
    pass

class CppComponentForm(ComponentForm):
    pass

class JavaComponentForm(ComponentForm):
    pass

class PlainTextComponentForm(ComponentForm):
    max_length = forms.IntegerField(min_value=0)

class AddSummissionForm(forms.Form):
    pass
    