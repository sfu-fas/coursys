from django.db import models
from coredata.models import Member
from jsonfield import JSONField
import decimal

class tug(models.Model):
	"""
	Time use guidline filled out by instructors 
	"""	
	member = models.ForeignKey(Member, null=False)
	base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
	config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
		# t.config['lab_prep']: Preparation for labs/tutorials
		# t.config['meetings']: Attendance at planning meetings with instructor
		# t.config['lectures']: Attendance at lectures
		# t.config['tutorials']: Attendance at labs/tutorials
		# t.config['office_hours']: Office hours/student consultation
		# t.config['Grading']
		# t.config['test_prep']: Quiz/exam preparation and invigilation
		# t.config['holliday']: Holliday compensation
		# t.config['other']
    
	def __unicode__(self):
		return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)
