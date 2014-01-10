from django import forms

from models import GradeSource

class GradeSourceForm(forms.ModelForm):
	class Meta:
		model = GradeSource
		