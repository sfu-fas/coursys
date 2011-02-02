from django.db import models
from django.forms import ModelForm
from timezones.fields import TimeZoneField
from django.template.defaultfilters import slugify
from courses.coredata.models import Person, Role

class Notes(models.Model):
	
	advisor = models.ForeignKey(Role)
	student = models.ForeignKey(Person)
	content = models.TextField( max_length = 1000)
	created_date = models.DateTimeField(auto_now = False, auto_now_add = False)

	def _unicode_(self):
		return '%s %s' % (self.advisor, self.student)

class NotesForm(ModelForm):
	class Meta:
		model = Notes

# Create your models here.
