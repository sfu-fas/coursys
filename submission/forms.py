from django import forms
from submission.models import *
from django.forms.widgets import Textarea, TextInput
from django.forms import ModelForm
from django.conf import settings
from django.utils.safestring import mark_safe

_required_star = '<em><img src="'+settings.MEDIA_URL+'icons/required_star.gif" alt="required"/></em>'

class ComponentForm(ModelForm):
    #override title to have 'required star'
    title = forms.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")', label=mark_safe("Title"+_required_star))


class ArchiveComponentForm(ComponentForm):
    class Meta:
        model = ArchiveComponent
        fields = ['title', 'description', 'max_size', 'position']
        widgets = {
            'description': Textarea(attrs={'cols': 50, 'rows': 5}),
            'max_size': TextInput(attrs={'style':'width:5em'}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class URLComponentForm(ComponentForm):
    class Meta:
        model = URLComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class CppComponentForm(ComponentForm):
    class Meta:
        model = CppComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class JavaComponentForm(ComponentForm):
    class Meta:
        model = JavaComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class PlainTextComponentForm(ComponentForm):
    class Meta:
        model = PlainTextComponent
        fields = ['title', 'description', 'max_length', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'max_length': TextInput(attrs={'style':'width:5em'}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }
