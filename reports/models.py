from django.db import models
from coredata.models import Role, Person, Unit, ROLE_CHOICES
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import datetime
import os
import sys
import copy
import traceback

import reportlib

REPORT_LOCATION = os.path.join( '.', 'reports', 'reportlib', 'reports' )

class Report(models.Model):
    name = models.CharField(help_text="Name of the report.", max_length=150, null=False)
    description = models.TextField(help_text="Description of the report.", null=True, blank=True)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def autoslug(self):
        return make_slug( self.name )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    
    def run(self):
        runnable_children = HardcodedReport.objects.filter(hidden=False, report=self)
        runs = []
        for child in runnable_children:
            runs.append(child.run())
        return runs[0]

def all_reports():
    return [(thing, thing) for thing in os.listdir(REPORT_LOCATION) if thing.endswith(".py")]

def report_map(report_location, logger):
    if report_location == 'fas_with_email.py':
        return reportlib.reports.FasStudentReport(logger)
    if report_location == 'immediate_retake_report.py':
        return reportlib.reports.ImmediateRetakeReport(logger)
    if report_location == 'five_retakes.py':
        return reportlib.reports.FiveRetakeReport(logger)

class RunLineLogger(object):
    def __init__(self, run):
        self.run = run
    def log(self, x):
        print x
        self.run.addLine(x)

class HardcodedReport(models.Model):
    report = models.ForeignKey(Report)
    file_location = models.CharField(help_text="The location of this report, on disk.", 
        max_length=80, choices=all_reports(), null=False)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def run(self):
        """ execute the code in this file """ 
        r = Run(report=self.report)
        r.save()
        logger = RunLineLogger(r)
        try:
            report_object = report_map(self.file_location, logger)
            report_object.run()
            for artifact in report_object.artifacts:
                artifact.convert_to_unicode()
                try:
                    result = Result(run=r, name=artifact.title, table=artifact.to_dict() )
                except AttributeError:
                    result = Result(run=r, table=artifact.to_dict() ) 
                result.save()
            r.success = True
            r.save()
        except Exception as e:
            logger.log("ERROR: " + str(e) )
            type_, value_, traceback_ = sys.exc_info()
            logger.log( ",".join(traceback.format_tb( traceback_ )) )
        return r

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

class Run(models.Model): 
    report = models.ForeignKey(Report)
    created_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    def autoslug(self):
        return make_slug( self.created_at )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    
    def addLine(self, message):
        r = RunLine(run=self, description=message)
        r.save()
    
    def getLines(self):
        return [ (line.created_at, line.description) for line in RunLine.objects.filter(run=self).order_by('created_at')]

class RunLine(models.Model):
    run = models.ForeignKey(Run)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

class Result(models.Model):
    run = models.ForeignKey(Run)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    table = JSONField(null=False, blank=False, default={})
    config = JSONField(null=False, blank=False, default={})

    cached_table = None
    cached_summary = None

    def table_rendered(self):
        """ Return the result as a reportlib.table.Table """
        if not self.cached_table:
            self.cached_table = reportlib.table.Table.from_dict(self.table)
        return self.cached_table
    
    def table_summary(self):
        """ Return the result as a reportlib.table.Table, but with only 5 rows. """
        if not self.cached_table:
            self.cached_table = reportlib.table.Table.from_dict(self.table)
        if not self.cached_summary:
            self.cached_summary = copy.deepcopy(self.cached_table)
            self.cached_summary.rows = self.cached_summary.rows[0:5]
        return self.cached_summary
    
    def autoslug(self):
        return make_slug( self.created_at )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
