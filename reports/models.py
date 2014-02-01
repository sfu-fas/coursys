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
import string
import importlib

from reportlib import DB2_Query
from reportlib.table import Table

REPORT_LOCATION = os.path.join( '.', 'reports', 'reportlib', 'reports' )

class Report(models.Model):
    """ 
        The core object of Reports. Contains Queries, Hardcoded Reports, Results, the
        whole nine yards.
    """
    name = models.CharField(help_text="Name of the report.", max_length=150, null=False)
    description = models.TextField(help_text="Description of the report.", null=True, blank=True)

    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def autoslug(self):
        return make_slug( self.name )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    
    def run(self):
        reports = HardcodedReport.objects.filter(report=self)
        queries = Query.objects.filter(report=self)
        
        runs = []
        for report in reports:
            runs.append(report.run())
        for report in queries:
            runs.append(report.run())
        if len(runs) > 0:
            return runs[0]
        else:
            return None

def all_reports():
    """
        Get a list of all of the available python hardcoded reports. 
    """
    return [(thing, thing) for thing in os.listdir(REPORT_LOCATION) 
                                        if thing.endswith(".py") and 
                                        not thing.startswith("__")]


class ReportLoadingException( Exception ):
    pass

def report_map(report_location, logger):
    """
        Given a report location - "fas_with_email.py" - import that file and load the report. 
    """
    report_without_extension = report_location[:-3]
    try:
        module = importlib.import_module("reports.reportlib.reports." + report_without_extension)
    except ImportError:
        raise ReportLoadingException( report_location + " could not be found in /reports/reportlib/reports/" )
    candidates = [item for item in dir(module) if item.endswith("Report") and item != "Report"] 
    if len(candidates) == 1:
        report_class = getattr(module, candidates[0])
        return report_class(logger)
    elif len(candidates) < 1:
        raise ReportLoadingException( "No Report could be found in " + report_location )
    else:
        raise ReportLoadingException( report_location + " loads more than one Report object." )

class HardcodedReport(models.Model):
    """
        Represents a report that exists as a python file in courses/reports/reportlib/reports
        ... yes, I understand how redundant redundant that path path is is 
    """
    report = models.ForeignKey(Report)
    file_location = models.CharField(help_text="The location of this report, on disk.", 
        max_length=80, choices=all_reports(), null=False)

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

class Query(models.Model):
    """ 
        A custom query developed by the user. 
    """
    report = models.ForeignKey(Report)
    name = models.CharField(max_length=150, null=False)
    query = models.TextField()
    
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def run(self):
        r = Run(report=self.report)
        r.save()
        logger = RunLineLogger(r)
        try:
            DB2_Query.set_logger(logger) 
            DB2_Query.connect()
            q = DB2_Query()
            q.query = string.Template(self.query)
            artifact = q.result()
            artifact.convert_to_unicode()
            result = Result(run=r, name=self.name, table=artifact.to_dict() )
            result.save()
            r.success = True
            r.save()
        except Exception as e:
            logger.log("ERROR: " + str(e) )
            type_, value_, traceback_ = sys.exc_info()
            logger.log( ",".join(traceback.format_tb( traceback_ )) )
        return r


class AccessRule(models.Model):
    """
        This person can see this report. 
    """
    report = models.ForeignKey(Report)
    person = models.ForeignKey(Person)
    notify = models.BooleanField(null=False, default=False, 
        help_text="Email this person when a report completes.")

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

class RunLineLogger(object):
    def __init__(self, run):
        self.run = run
    def log(self, x):
        print x
        self.run.addLine(x)

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

    def autoslug(self):
        if self.name: 
            return make_slug( self.name )
        else: 
            return make_slug( self.id )
    
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    cached_table = None
    cached_summary = None

    def table_rendered(self):
        """ Return the result as a reportlib.table.Table """
        if not self.cached_table:
            self.cached_table = Table.from_dict(self.table)
        return self.cached_table
    
    def table_summary(self):
        """ Return the result as a reportlib.table.Table, but with only 5 rows. """
        if not self.cached_table:
            self.cached_table = Table.from_dict(self.table)
        if not self.cached_summary:
            self.cached_summary = copy.deepcopy(self.cached_table)
            self.cached_summary.rows = self.cached_summary.rows[0:5]
        return self.cached_summary
    
