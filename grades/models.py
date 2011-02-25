from django.db import models
from autoslug import AutoSlugField
from timezones.fields import TimeZoneField
from coredata.models import Member, CourseOffering
from dashboard.models import *
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.core.cache import cache
from datetime import datetime, timedelta

FLAG_CHOICES = [
    ('NOGR', 'no grade'),
    ('GRAD', 'graded'), 
    ('CALC', 'calculated'), 
    ('EXCU', 'excused'), 
    ('DISH', 'academic dishonesty') ]
FLAGS = dict(FLAG_CHOICES)

ACTIVITY_STATUS_CHOICES = [
    ('RLS', 'grades released'),
    ('URLS', 'grades not released to students'),
    ('INVI', 'activity not visible to students') ]
ACTIVITY_STATUS = dict(ACTIVITY_STATUS_CHOICES)
# but see also overridden get_status_display method on Activity

LETTER_GRADE_CHOICES = [
    ('A+', 'A+ - Excellent performance'),
    ('A', 'A - Excellent performance'),
    ('A-', 'A- - Excellent performance'),
    ('B+', 'B+ - Good performance'),
    ('B', 'B - Good performance'),
    ('B-', 'B- - Good performance'),
    ('C+', 'C+ - Satisfactory performance'),
    ('C', 'C - Satisfactory performance'),
    ('C-', 'C- - Marginal performance'),
    ('D', 'D - Marginal performance'),
    ('F', 'F - Fail(Unsatisfactory performance)'),
    ('FD', 'FD - Fail(Academic discipline)'),
    ('N', 'N - Did not write exam or did not complete course'),
    ('P', 'P - Satisfactory performance or better (pass, ungraded)'),
    ('W', 'W - Withdrawn'),
    ('AE', 'AE - Aegrotat standing, compassionate pass'),
    ('AU', 'AU - Audit'),
    ('CC', 'CC - Course challenge'),
    ('CF', 'CF - Course challenge fail'),
    ('CN', 'CN - Did not complete challenge'),
    ('CR', 'CR - Credit without grade'),
    ('FX', 'FX - Formal exchange'),
    ('WD', 'WD - Withdrawal'),
    ('WE', 'WE - Withdrawal under extenuating circumstances'),
    ('DE', 'DE - Deferred grade'),
    ('GN', 'GN - Grade not reported'),
    ('IP', 'IP - In progress') ]
LETTER_GRADE = dict(LETTER_GRADE_CHOICES)

class Activity(models.Model):
    """
    Generic activity (i.e. column in the gradebook that can have a value assigned for each student).
    This should never be instantiated directly: only its sublcasses should.
    """
    name = models.CharField(max_length=30, db_index=True, help_text='Name of the activity.')
    short_name = models.CharField(max_length=15, db_index=True, help_text='Short-form name of the activity.')
    slug = AutoSlugField(populate_from='short_name', null=False, editable=False, unique_with='offering')
    status = models.CharField(max_length=4, null=False, choices=ACTIVITY_STATUS_CHOICES, help_text='Activity status.')
    due_date = models.DateTimeField(null=True, help_text='Activity due date')
    percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    position = models.PositiveSmallIntegerField(help_text="The order of displaying course activities.")
    group = models.BooleanField(null=False, default=False)
    deleted = models.BooleanField(null = False, db_index = True, default=False)
    url = models.URLField(verify_exists=True, null=True)
    
    offering = models.ForeignKey(CourseOffering)

    def __unicode__(self):
        return "%s - %s" % (self.offering, self.name)
    def short_str(self):
        return self.name
    def __cmp__(self, other):
        return cmp(self.position, other.position)
    def get_absolute_url(self):
        return reverse('grades.views.activity_info', kwargs={'course_slug': self.offering.slug, 'activity_slug': self.slug})
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    def is_numeric(self):
        return False
    class Meta:
        verbose_name_plural = "activities"
        ordering = ['deleted', 'position']

    def save(self, force_insert=False, force_update=False, newsitem=True, *args, **kwargs):
        # get old status so we can see if it's newly-released
        try:
            old = Activity.objects.get(id=self.id)
        except Activity.DoesNotExist:
            old = None
        super(Activity, self).save(*args, **kwargs)

        if newsitem and old and self.status == 'RLS' and old != None and old.status != 'RLS':
            # newly-released grades: create news items
            class_list = Member.objects.exclude(role="DROP").filter(offering=self.offering)
            for m in class_list:
                n = NewsItem(user=m.person, author=None, course=self.offering,
                    source_app="grades", title="%s grade released" % (self.name), 
                    content='Grades have been released for "%s in %s":%s.' \
                      % (self.name, self.offering.name(), self.get_absolute_url()),
                    url=self.get_absolute_url()
                    )
                n.save()
    
    def display_label(self):
        if self.percent:
            return "%s (%s%%)" % (self.name, self.percent)
        else:
            return "%s" % (self.name)
        
    def display_grade_student(self, student):
        """
        String representing grade for this student
        """
        if self.status=="URLS":
            return u'\u2014'
        elif self.status=="INVI":
            raise RuntimeError, "Can't display invisible grade."
        else:
            return self.display_grade_visible(student)

    def display_grade_staff(self, student):
        """
        String representing grade for this student
        """
        return self.display_grade_visible(student)
    def get_status_display(self):
        """
        Override to provide better string for not-yet-due case.
        """
        if self.status == "URLS" and self.due_date and self.due_date > datetime.now():
            return "no grades: due date not passed"

        return ACTIVITY_STATUS[self.status]

    def markable(self):
        """
        Returns True if this activity is "markable".  i.e. has any marking components defined.
        """
        return self.activitycomponent_set.all().count() != 0

    def submitable(self):
        """
        Returns True if this activity is "submittable".
        i.e. has any submission components defined and within 30 days after due date
        """
        comp_count = self.submissioncomponent_set.filter(deleted=False).count()
        return comp_count != 0 and not self.too_old()
    def no_submit_too_old(self):
        """
        Returns True if this activity was submittable but is now too old
        """
        comp_count = self.submissioncomponent_set.filter(deleted=False).count()
        return comp_count != 0 and self.too_old()
    def too_old(self):
        """
        Returns True if this activity is not submittable because it is too old
        """
        now = datetime.now()
        return now - self.due_date >= timedelta(days=30)
    
    def SubmissionClass(self):
        from submission.models import StudentSubmission, GroupSubmission
        if self.group:
            return GroupSubmission
        else:
            return StudentSubmission

    def due_in_str(self):
        """
        Produce pretty string for "in how long is this due"
        """
        if not self.due_date:
            return u"\u2014"
        due_in = self.due_date - datetime.now()
        seconds = (due_in.microseconds + (due_in.seconds + due_in.days * 24 * 3600.0) * 10**6) / 10**6
        if due_in < timedelta(seconds=0):
            return u'\u2014'
        elif due_in > timedelta(days=2):
            return "%i days" % (due_in.days)
        elif due_in > timedelta(days=1):
            return "%i day %i hours" % (due_in.days, int((seconds/3600) - (due_in.days*24)))
        elif due_in > timedelta(hours=2):
            return "%i hours %i minutes" % (int(seconds/3600), int(seconds%3600/60))
        elif due_in > timedelta(hours=1):
            return "%i hour %i minutes" % (int(seconds/3600), int(seconds%3600/60))
        else:
            return "%i minutes" % (int(seconds/60))
        
    def due_class(self):
        """
        Produce class name for "heat": how long until it is due?
        """
        if not self.due_date:
            return "due_unknown"
        due_in = self.due_date - datetime.now()
        if due_in < timedelta(seconds=0):
            return "due_overdue"
        elif due_in < timedelta(days=2):
            return "due_verysoon"
        elif due_in < timedelta(days=7):
            return "due_soon"
        else:
            return "due_far"


class NumericActivity(Activity):
    """
    Activity with a numeric mark
    """
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)
    

    class Meta:
        verbose_name_plural = "numeric activities"
    def type_long(self):
        return "Numeric Graded"
    def is_numeric(self):
        return True
    def is_calculated(self):
        return False

    def display_grade_visible(self, student):
        grades = NumericGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0:
            grade = u'\u2014'
        elif grades[0].flag == "NOGR":
            grade = u'\u2014'
        else:
            grade = grades[0].value
        return "%s/%s" % (grade, self.max_grade)



class LetterActivity(Activity):
    """
    Activity with a letter grade
    """
    class Meta:
        verbose_name_plural = "letter activities"
    def type_long(self):
        return "Letter Graded"
    def is_numeric(self):
        return False
    def is_calculated(self):
        return False
    
    def display_grade_visible(self, student):
        grades = LetterGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0:
            grade = u'\u2014'
        elif grades[0].flag == "NOGR":
            grade = u'\u2014'
        else:
            grade = str(grades[0].letter_grade)
        return grade


class CalNumericActivity(NumericActivity):
    """
    Activity with a calculated numeric grade which is the final numeric grade of the course offering
    """
    formula = models.CharField(max_length=250, help_text='parsed formula to calculate final numeric grade')

    def is_calculated(self):
        return True
    class Meta:
        verbose_name_plural = "cal numeric activities"
    def type_long(self):
        return "Calculated Numeric Grade"

class CalLetterActivity(LetterActivity):
    """
    Activity with a calculated letter grade which is the final letter grade of the course offering
    """
    numeric_activity = models.ForeignKey(NumericActivity, related_name='numeric_source_set')
    exam_activity = models.ForeignKey(Activity, null=True, related_name='exam_set')
    letter_cutoff_formula = models.CharField(max_length=250, help_text='parsed formula to calculate final letter grade')
    
    class Meta:
        verbose_name_plural = 'cal letter activities'
    def type_long(self):
        return "Calculated Letter Grade"
    def is_calculated(self):
        return True





# list of all subclasses of Activity:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
ACTIVITY_TYPES = [CalNumericActivity, NumericActivity, CalLetterActivity, LetterActivity]

def all_activities_filter(offering, slug=None):
    """
    Return all activities as their most specific class.
    
    This isn't pretty, but it will do the job.
    """
    #key = "all_act_filt" + '_' + offering.slug
    filter_args = {'offering':offering}
    if slug:
        filter_args['slug'] = slug
        #key += "_" + slug

    #data = cache.get(key)
    #if data:
    #    return data
    
    activities = [] # list of activities
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for ActivityType in ACTIVITY_TYPES:
        acts = list(ActivityType.objects.filter(deleted=False, **filter_args).select_related('offering'))
        activities.extend( (a for a in acts if a.id not in found) )
        found.update( (a.id for a in acts) )

    activities.sort()
    #cache.set(key, activities, 60)
    return activities


class NumericGrade(models.Model):
    """
    Individual numeric grade for a NumericActivity.
    """
    activity = models.ForeignKey(NumericActivity, null=False)
    member = models.ForeignKey(Member, null=False)

    value = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=False)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default = 'NOGR')
    comment = models.TextField(null=True)
    
    def __unicode__(self):
        return "Member[%s]'s grade[%s] for [%s]" % (self.member.person.userid, self.value, self.activity)
    def get_absolute_url(self):
        return reverse('grades.views.student_info', kwargs={'course_slug': self.offering.slug, 'userid': self.member.person.userid})

    def display_staff(self):
        if self.flag == 'NOGR':
            return u'\u2014'
        else:
            return "%s/%s" % (self.value, self.activity.max_grade)

    def display_staff_short(self):
        if self.flag == 'NOGR':
            return ''
        else:
            return "%.1f" % (self.value)
    
    def display_with_percentage_student(self):
        """
        Display student grade with percentage from student view, e.g 12/15 (80.00%)
        """
        if self.activity.status == 'URLS':
            return u'\u2014'
        elif self.activity.status == "INVI":
            raise RuntimeError, "Can't display invisible grade."
        elif self.flag == "NOGR":
            return u'\u2014'
        else:
            return '%s/%s (%.2f%%)' % (self.value, self.activity.max_grade, float(self.value)/float(self.activity.max_grade)*100)
        

    def save(self, newsitem=True):
        if self.flag == "NOGR":
            # make sure "no grade" values have a zero: just in case the value is used in some other calc
            self.value = 0

        super(NumericGrade, self).save()
        if self.activity.status == "RLS" and newsitem and self.flag != "NOGR":
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name), 
                content='A "new grade for %s":%s in %s is available.' 
                  % (self.activity.name, self.activity.get_absolute_url(), self.activity.offering.name()),
                url=self.activity.get_absolute_url())
            n.save()

    def get_absolute_url(self):
        """        
        for regular numeric activity return the mark summary page
        but for calculate numeric activity only return the activity information page
        because there is no associated mark summary record
        """
        if CalNumericActivity.objects.filter(id=self.activity.id):
            return reverse("grades.views.activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        else:
            return reverse("marking.views.mark_summary_student", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug, 'userid':self.member.person.userid})
    class Meta:
        unique_together = (('activity', 'member'),)


##############################Yu Liu Added#########################################################     
class LetterGrade(models.Model):
    """
    Individual letter grade for a LetterActivity
    """
    activity = models.ForeignKey(LetterActivity, null=False)
    member = models.ForeignKey(Member, null=False)
    
    letter_grade = models.CharField(max_length=2, null=False, choices=LETTER_GRADE_CHOICES)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default = 'NOGR')
    comment = models.TextField(null=True)
    
    def __unicode__(self):
        return "Member[%s]'s letter grade[%s] for [%s]" % (self.member.person.userid, self.letter_grade, self.activity)

    def display_staff(self):
        if self.flag == 'NOGR':
            return u'\u2014'
        else:
            return "%s" % (self.letter_grade)
    def get_absolute_url(self):
        return reverse('grades.views.student_info', kwargs={'course_slug': self.offering.slug, 'userid': self.member.person.userid})
    
    def save(self, newsitem=True):
        super(LetterGrade, self).save()
        if self.activity.status=="RLS" and newsitem and self.flag != "NOGR":
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name), 
                content='A "new grade for %s":%s in %s is available.' 
                  % (self.activity.name, self.get_absolute_url(), self.activity.offering.name()),
                url=self.get_absolute_url())
            n.save()
    def get_absolute_url(self):
        """        
        for regular numeric activity return the mark summary page
        but for calculate numeric activity only return the activity information page
        because there is no associated mark summary record
        """
        if CalNumericActivity.objects.filter(id=self.activity.id):
            return reverse("grades.views.activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        else:
            return reverse("marking.views.mark_summary_student", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug, 'userid':self.member.person.userid})
            
    class Meta:
        unique_together = (('activity', 'member'), )

##############################Yu Liu Added#########################################################  

NumericActivity.GradeClass = NumericGrade
LetterActivity.GradeClass = LetterGrade

def neaten_activity_positions(course):
    """
    update all positions to consecutive integers: seems possible to get identical positions in some cases
    """
    count = 1
    for a in Activity.objects.filter(offering=course).order_by('position'):
        a.position = count
        a.save()
        count += 1

