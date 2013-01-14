from django.db import models
from jsonfield import JSONField
from coredata.models import Unit, Person

class GuestAccount(models.Model):
	name = models.CharField(max_length = 30)
	#unit = models.ForeignKey('')

class guest_platform(models.Model):
	name = models.CharField(max_length = 50)
	#unit = models.ForeignKey('')

class guest_account_booking(models.Model):
	guestaccount = models.ForeignKey('guest_account')
	bookername = models.CharField(max_length = 30)
	bookeremail = models.EmailField()
	#authorizer = models.ForeignKey('')
	platforms = models.ManyToManyField(guest_platform)
	#guest_platform.unit == guest_account_booking.authorizer.unit??
	assigned = models.CharField(max_length = 30)
	password = models.CharField(max_length = 75)
	startdate = models.DateField()
	enddate = models.DateField()
	status_choices = (
		('B', 'Booked'),
		('C', 'Closed'),
		('E', 'Expired'),
	)
	STATUS = models.CharField(max_length = 1,
				choices = status_choices,
				default = 'C')

	RTticket = models.URLField()	
	comments = models.TextField()
	deleted = models.BooleanField(default = False)
	config = JSONField(null=False, blank=False, default={})
