from django.db import models
from coredata.models import Role, Person, Unit, ROLE_CHOICES
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import datetime
import os

REPORT_LOCATION = os.path.join( '.', 'reports', 'reportlib', 'reports' )

class Report(models.Model):
    name = models.CharField(help_text="Name of the report.", max_length=150, null=False)
    description = models.TextField(help_text="Description of the report.", null=True, blank=True)
    last_run = models.DateTimeField(null=True, default=None)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def autoslug(self):
        return make_slug( self.name )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    
    def run(self):
        runnable_children = HardcodedReport.objects.filter(hidden=False, report=self)
        for child in runnable_children:
            child.run()
        return

def all_reports():
    return [(thing, thing) for thing in os.listdir(REPORT_LOCATION) if thing.endswith(".py")]

class HardcodedReport(models.Model):
    report = models.ForeignKey(Report)
    file_location = models.CharField(help_text="The location of this report, on disk.", 
        max_length=80, choices=all_reports(), null=False)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    
    # TODO: on save, make sure that this report exists in that file location

    def run(self):
        """ execute the code in this file """ 
        # TODO put code in here
        return 

class AccessRule(models.Model):
    report = models.ForeignKey(Report)
    unit = models.ForeignKey(Unit, null=False)
    viewable_by = models.CharField(max_length=4, choices=ROLE_CHOICES)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

# Schedule
# When do we run this report? 

SCHEDULE_TYPE_CHOICES = (
        ('DAI', 'Daily'),
        ('MON', 'Monthly'),
        ('YEA', 'Yearly'),
        ('ONE', 'One-Time'),
)

def increment_year(date):
    return datetime.datetime( date.year+1, date.month, date.day, date.hour, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )

def increment_month(date):
    if date.month >= 12: 
        return datetime.datetime( date.year+1, 1, date.day, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )
    else:
        return datetime.datetime( date.year, date.month+1, date.day, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )

def increment_day(date):
    if date.day >= 29:
        return increment_month( datetime.datetime(date.year, date.month, 1, date.hour, date.minute, date.second, date.microsecond, date.tzinfo) )
    else:
        return datetime.datetime( date.year, date.month, date.day+1, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )


class ScheduleRule(models.Model):
    report = models.ForeignKey(Report)
    schedule_type = models.CharField(max_length=3, choices=SCHEDULE_TYPE_CHOICES)
    last_run = models.DateTimeField() # the last time this ScheduleRule was run
    next_run = models.DateTimeField() # the next time to run this ScheduleRule

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def set_next_run(self):
        last_run = next_run
        if schedule_type == 'DAI': 
            next_run = increment_day( next_run )
        if schedule_type == 'MON':
            next_run = increment_month( next_run )
        if schedule_type == 'YEA':
            next_run = increment_year( next_run )
        if schedule_type == 'ONE': 
            next_run = None
        save()

#class Result(models.Model):
# Result
# The output of a report, as a JSON object. 

