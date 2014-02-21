from django.db import models
from coredata.models import Role, Person, Unit, ROLE_CHOICES
from alerts.models import AlertType, Alert
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from dashboard.models import NewsItem
from django.core.urlresolvers import reverse
from django.conf import settings

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
        The core object of Reports. Contains Queries, Hardcoded Reports, 
        Results, the whole nine yards.
    """
    name = models.CharField(help_text="Name of the report.", 
                            max_length=150, null=False)
    description = models.TextField(help_text="Description of the report.", 
                                   null=True, blank=True)

    alert = models.ForeignKey(AlertType, null=True)
    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def autoslug(self):
        return make_slug( self.name )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, 
                         unique=True)

    def expired_schedule_rules(self):
        return ScheduleRule.objects.filter(next_run__lte=datetime.datetime.now(),
                                           report=self)

    def is_scheduled_to_run(self):
        """
        Returns true if this Report has a run queued. 
        """
        return len(self.expired_schedule_rules()) > 0
    
    def run(self):
        hardcoded_reports = HardcodedReport.objects.filter(report=self)
        queries = Query.objects.filter(report=self)

        runs = []
        for report in hardcoded_reports:
            runs.append(report.run())
        for query in queries:
            runs.append(query.run())
        
        if self.alert:
            for run in runs: 
                for result in run.result_set.all():
                    for row_map in result.table_rendered().row_maps():
                        if 'EMPLID' in row_map:
                            # for more complicated Alert handling, we need
                            # to pass in actual unique_fields
                            unique_fields = ["EMPLID"]
                            Alert.create(row_map, self.alert, unique_fields)

        for rule in self.expired_schedule_rules():
            rule.set_next_run()
            rule.save()

        failed_runs = [run for run in runs if run.success == False]
        if len(failed_runs) > 0:
            self.failure_notification(failed_runs[0])

        return runs
    
    def failure_notification(self, failed_run):
        every_sysadmin = [role.person for role in Role.objects.filter(role='SYSA')]
        for sysadmin in every_sysadmin:
            n = NewsItem( user=sysadmin,
                            source_app='reports',
                            title="Failed Report: " + self.name, 
                            url= reverse('reports.views.view_run', kwargs={'report':self.slug, 'run':failed_run.slug}),
                            content= "A run has failed! \n" + self.description );
            n.save()

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
        module = importlib.import_module("reports.reportlib.reports." + 
                                         report_without_extension)
    except ImportError as e:
        raise ReportLoadingException( report_location + " : " + str(e) )

    candidates = [item for item in dir(module) if item.endswith("Report") 
                  and item != "Report"] 

    if len(candidates) == 1:
        report_class = getattr(module, candidates[0])
        return report_class(logger)
    elif len(candidates) < 1:
        raise ReportLoadingException( "No Report could be found in " + 
                                     report_location )
    else:
        raise ReportLoadingException( report_location + 
                                     " loads more than one Report object." )

class HardcodedReport(models.Model):
    """
        Represents a report that exists as a python file in 
        courses/reports/reportlib/reports
    """
    report = models.ForeignKey(Report)
    file_location = models.CharField(help_text="The location of this report, on disk.", 
        max_length=80, choices=all_reports(), null=False)

    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def run(self):
        """ execute the code in this file """ 
        r = Run(report=self.report, name=self.file_location)
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
        r = Run(report=self.report, name=self.name)
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

    def send_notification(self, run):
        n = NewsItem( user= self.person, 
                        source_app='reports',
                        title="Completed Run: " + self.report.name + " : " + run.slug, 
                        url= reverse('reports.views.view_run', kwargs={'report':self.report.slug, 'run':run.slug}),
                        content= "You have a scheduled report that has completed! \n" + self.report.description );
        n.save()


# Schedule
# When do we run this report? 

SCHEDULE_TYPE_CHOICES = (
        ('ONE', 'One-Time'),
        ('DAI', 'Daily'),
        ('MON', 'Monthly'),
        ('YEA', 'Yearly'),
)


def increment_year(date):
    # the only special case I can think of is leap years. 
    if date.month == 2 and date.day == 29:
        return datetime.datetime( date.year+1, date.month, 28, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )
    return datetime.datetime( date.year+1, date.month, date.day, date.hour, date.minute, date.second, date.microsecond, date.tzinfo )


def increment_month(date):
    """
    There's a bit of a strange special case here. 
    
    "End of the month" is traditionally a pretty important day to schedule
    things, so if you're at the end of the current month, this function will
    attempt to smoothly transition you to the end of the next month.

    On top of that, it is impossible to smoothly transition from Jan 30 to 
    Feb 30 (as such a date does not exist), so Jan 30 will transition to
    Feb 28 (the end of the month). However, this loses information - the next
    time a month with 31 days comes around, the report will run at the end
    of the month rather than on the 30th as initially intended. 

    This means, functionally, that any date after the 28th of the month
    will be treated as "the end of the month" for the purposes of calculating
    when the next report should be run. 
    """
    import calendar

    if date.month == 12:
        year = date.year + 1
        month = 1
    else:
        year = date.year
        month = date.month + 1

    end_of_this_month = calendar.monthrange(date.year, date.month)[1]
    end_of_next_month = calendar.monthrange(year, month)[1]

    day = date.day
    if day == end_of_this_month or date.day >= end_of_next_month:
        day = end_of_next_month

    return datetime.datetime( year, month, day, date.hour, date.minute, 
                             date.second,
                             date.microsecond, date.tzinfo )


def increment_day(date):
    new_date = date + datetime.timedelta(days=1)
    return new_date


class ScheduleRule(models.Model):
    """
    Run this Report at this time. 
    """
    report = models.ForeignKey(Report)
    schedule_type = models.CharField(max_length=3, 
                                     choices=SCHEDULE_TYPE_CHOICES,
                                     null=False,
                                     default="ONE")
    last_run = models.DateTimeField(null=True) # the last time this ScheduleRule was run
    next_run = models.DateTimeField() # the next time to run this ScheduleRule

    config = JSONField(null=False, blank=False, default={})
    created_at = models.DateTimeField(auto_now_add=True)

    def set_next_run(self):
        self.last_run = self.next_run
        if self.schedule_type == 'DAI': 
            self.next_run = increment_day( self.next_run )
        if self.schedule_type == 'MON':
            self.next_run = increment_month( self.next_run )
        if self.schedule_type == 'YEA':
            self.next_run = increment_year( self.next_run )
        if self.schedule_type == 'ONE': 
            self.next_run = None

        # if this doesn't get the run to past the current date, try again. 
        if self.next_run < datetime.datetime.now():
            self.set_next_run()


def schedule_ping():
    import shutil
    rules = ScheduleRule.objects.filter(next_run__lte=datetime.datetime.now())
    reports = [rule.report for rule in rules]
    set_of_reports_that_need_to_be_run = set(reports)
    for report in set_of_reports_that_need_to_be_run:
        report.run()
    shutil.rmtree(settings.REPORT_CACHE_LOCATION)


class Run(models.Model): 
    report = models.ForeignKey(Report)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=150, null=False)
    success = models.BooleanField(default=False)
    def autoslug(self):
        return make_slug( self.created_at )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    
    def addLine(self, message):
        r = RunLine(run=self, description=message)
        r.save()
    
    def getLines(self):
        return [ (line.created_at, line.description) for line in RunLine.objects.filter(run=self).order_by('created_at')]
    
    def save(self, *args, **kwargs):
        super(Run, self).save(*args, **kwargs)
        #TODO: should we send these on failure too? 
        if self.success: 
            notify_targets = AccessRule.objects.filter(report=self.report, notify=True)
            for target in notify_targets:
                target.send_notification(self)

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
