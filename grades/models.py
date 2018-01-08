from django.db import models
from autoslug import AutoSlugField
from coredata.models import Member, CourseOffering, Person
from dashboard.models import NewsItem
from django.db import transaction
from django.db.models import Count
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta, date
from courselib.json_fields import JSONField
from courselib.json_fields import getter_setter
from courselib.slugs import make_slug
import decimal, json

COMMENT_LENGTH = 5000

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

GPA_GRADE_CHOICES = [
    ('A+', 'A+ (Excellent performance)'),
    ('A', 'A (Excellent performance)'),
    ('A-', 'A- (Excellent performance)'),
    ('B+', 'B+ (Good performance)'),
    ('B', 'B (Good performance)'),
    ('B-', 'B- (Good performance)'),
    ('C+', 'C+ (Satisfactory performance)'),
    ('C', 'C (Satisfactory performance)'),
    ('C-', 'C- (Marginal performance)'),
    ('D', 'D (Marginal performance)'),
    ('F', 'F (Fail. Unsatisfactory Performance)'),
    ]

NON_GPA_GRADE_CHOICES = [
    #('FD', 'FD (Fail (Academic discipline))'),
    ('N', 'N (Did not write exam or did not complete course)'),
    ('P', 'P (Satisfactory performance or better (pass, ungraded))'),
    #('W', 'W (Withdrawn)'),
    #('AE', 'AE (Aegrotat standing, compassionate pass)'),
    #('AU', 'AU (Audit)'),
    #('CC', 'CC (Course challenge)'),
    #('CF', 'CF (Course challenge fail)'),
    #('CN', 'CN (Did not complete challenge)'),
    #('CR', 'CR (Credit without grade)'),
    #('FX', 'FX (Formal exchange)'),
    #('WD', 'WD (Withdrawal)'),
    #('WE', 'WE (Withdrawal under extenuating circumstances)'),
    ('DE', 'DE (Deferred grade)'),
    ('GN', 'GN (Grade not reported)'),
    ('IP', 'IP (In progress)'),
    ]

LETTER_GRADE_CHOICES = GPA_GRADE_CHOICES + NON_GPA_GRADE_CHOICES
LETTER_GRADE = dict(LETTER_GRADE_CHOICES)
LETTER_GRADE_CHOICES_IN = set(LETTER_GRADE.keys())

class Activity(models.Model):
    """
    Generic activity (i.e. column in the gradebook that can have a value assigned for each student).
    This should never be instantiated directly: only its sublcasses should.
    """
    objects = models.Manager()
    
    name = models.CharField(max_length=30, db_index=True, help_text='Name of the activity.')
    short_name = models.CharField(max_length=15, db_index=True, help_text='Short-form name of the activity.')
    def autoslug(self):
        return make_slug(self.short_name)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='offering', manager=objects,
                         help_text='String that identifies this activity within the course offering')
    status = models.CharField(max_length=4, null=False, choices=ACTIVITY_STATUS_CHOICES, help_text='Activity status.')
    due_date = models.DateTimeField(null=True, help_text='Activity due date')
    percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    position = models.PositiveSmallIntegerField(help_text="The order of displaying course activities.")
    group = models.BooleanField(null=False, default=False)
    deleted = models.BooleanField(null = False, db_index = True, default=False)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # a.config['url'] (string, default None): URL for more info
        # a.config['showstats'] (boolean, default True): show students summary stats for this activity?
        # a.config['showhisto'] (boolean, default True): show students histogram for this activity?
        # a.config['showformula'] (boolean, default False): show students formula/cutoffs for this activity?
        # a.config['multisubmit'] (boolean, default False): Use the "submit many times" behaviour?
        # a.config['calculation_leak'] (boolean, default False): For CalNumericActivity, include unreleased grades when calculating? (Thus possibly leaking URLS values to students)
        # TODO: showformula not actually implemented yet
    
    offering = models.ForeignKey(CourseOffering)
    
    defaults = {'url': '', 'showstats': True, 'showhisto': True, 'showformula': False, 'multisubmit': False, 'calculation_leak': False}
    url, set_url = getter_setter('url')
    showstats, set_showstats = getter_setter('showstats')
    showhisto, set_showhisto = getter_setter('showhisto')
    showformula, set_showformula = getter_setter('showformula')
    multisubmit, set_multisubmit = getter_setter('multisubmit')
    calculation_leak, set_calculation_leak = getter_setter('calculation_leak')

    def __unicode__(self):
        return "%s - %s" % (self.offering, self.name)
    def short_str(self):
        return self.name
    def __cmp__(self, other):
        return cmp(self.position, other.position)
    def get_absolute_url(self):
        return reverse('offering:activity_info', kwargs={'course_slug': self.offering.slug, 'activity_slug': self.slug})
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    def is_numeric(self):
        return False
    class Meta:
        verbose_name_plural = "activities"
        ordering = ['deleted', 'position']
        unique_together = (('offering', 'slug'),)

    def save(self, force_insert=False, force_update=False, newsitem=True, entered_by=None, *args, **kwargs):
        # get old status so we can see if it's newly-released
        try:
            old = Activity.objects.get(id=self.id)
        except Activity.DoesNotExist:
            old = None
        
        # reset slugs before semester starts
        if self.offering.semester.start > date.today():
            self.slug = None
        
        super(Activity, self).save(*args, **kwargs)

        if newsitem and old and self.status == 'RLS' and old != None and old.status != 'RLS':
            from grades.tasks import send_grade_released_news, create_grade_released_history

            # newly-released grades: record that grade was released
            assert entered_by
            entered_by = get_entry_person(entered_by)
            create_grade_released_history(self.id, entered_by.id)

            # newly-released grades: create news items
            send_grade_released_news(self.id)

        if old and old.group and not self.group:
            # activity changed group -> individual. Clean out any group memberships
            from groups.models import GroupMember
            GroupMember.objects.filter(activity=self).delete()
    
    def safely_delete(self):
        """
        Do the actions to safely "delete" the activity.
        """
        with transaction.atomic():
            # mangle name and short-name so instructors can delete and replace
            i = 1
            while True:
                suffix = "__%04i" % (i)
                existing = Activity.objects.filter(offering=self.offering, name=self.name+suffix).count() \
                        + Activity.objects.filter(offering=self.offering, short_name=self.short_name+suffix).count()
                if existing == 0:
                    break
                i += 1

            # update the activity
            self.deleted = True
            self.name = self.name + suffix
            self.short_name = self.short_name + suffix
            self.slug = None
            self.save()

    def display_label(self):
        if self.percent:
            return "%s (%s%%)" % (self.name, self.percent)
        else:
            return "%s" % (self.name)
        
    def display_grade_student(self, student):
        """
        String representing grade for this student
        """
        return self.display_grade_visible(student, 'STUD')

    def display_grade_staff(self, student):
        """
        String representing grade for this student
        """
        return self.display_grade_visible(student, 'INST')

    def get_status_display(self):
        """
        Override to provide better string for not-yet-due case.
        """
        if self.status == "URLS" and self.due_date and self.due_date > datetime.now():
            return "no grades: due date not passed"

        return ACTIVITY_STATUS[self.status]

    def get_status_display_staff(self):
        """
        Override to provide better string for not-yet-due case.
        """
        if self.status == "URLS" and self.due_date and self.due_date > datetime.now():
            return "no grades: due date not passed"
        elif self.status == 'URLS':
            total = Member.objects.filter(offering=self.offering, role='STUD').count()
            if isinstance(self, NumericActivity):
                GradeClass = NumericGrade
            elif isinstance(self, LetterActivity):
                GradeClass = LetterGrade
            graded = GradeClass.objects.filter(activity=self).exclude(flag='NOGR').count()
            # If we've graded everything, might as well change the status back
            if graded == total and total > 0:
                return ACTIVITY_STATUS[self.status]
            # Otherwise, let them know the progress.
            return 'ready to grade (%i/%i graded)' % (graded, total)

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
        if not self.due_date:
            return False
        now = datetime.now()
        return now - self.due_date >= timedelta(days=30)
    
    def SubmissionClass(self):
        from submission.models import StudentSubmission, GroupSubmission
        if self.group:
            return GroupSubmission
        else:
            return StudentSubmission

    def due_in_future(self):
        return self.due_date and self.due_date > datetime.now()

    def due_in_str(self):
        """
        Produce pretty string for "in how long is this due"
        """
        if not self.due_date:
            return "\u2014"
        due_in = self.due_date - datetime.now()
        seconds = (due_in.microseconds + (due_in.seconds + due_in.days * 24 * 3600.0) * 10**6) / 10**6
        if due_in < timedelta(seconds=0):
            return '\u2014'
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
    max_grade = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name_plural = "numeric activities"

    def type_long(self):
        return "Numeric Graded"

    def is_numeric(self):
        return True

    def is_calculated(self):
        return False

    def get_grade(self, student, role):
        if role == 'STUD':
            if self.status == 'INVI':
                raise RuntimeError("Can't display invisible grade.")
            elif self.status == 'URLS':
                return None

        grades = NumericGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0 or grades[0].flag == "NOGR":
            return None
        else:
            return grades[0]

    def display_grade_visible(self, student, role):
        grade = self.get_grade(student, role)
        if grade:
            return "%s/%s" % (grade.value, self.max_grade)
        else:
            return '\u2014'



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

    def get_grade(self, student, role):
        if role == 'STUD':
            if self.status == 'INVI':
                raise RuntimeError("Can't display invisible grade.")
            elif self.status == 'URLS':
                return None

        grades = LetterGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0 or grades[0].flag == "NOGR":
            return None
        else:
            return grades[0]

    def display_grade_visible(self, student, role):
        grade = self.get_grade(student, role)
        if grade:
            return str(grade.letter_grade)
        else:
            return '\u2014'


class CalNumericActivity(NumericActivity):
    """
    Activity with a calculated numeric grade which is the final numeric grade of the course offering
    """
    formula = models.TextField(help_text='parsed formula to calculate final numeric grade', default="[[activitytotal]]")

    def is_calculated(self):
        return True

    class Meta:
        verbose_name_plural = "cal numeric activities"

    def type_long(self):
        return "Calculated Numeric Grade"

    def formula_display(self):
        from grades.formulas import display_formula
        activities = all_activities_filter(self.offering)
        return display_formula(self, activities)

class CalLetterActivity(LetterActivity):
    """
    Activity with a calculated letter grade which is the final letter grade of the course offering
    """
    numeric_activity = models.ForeignKey(NumericActivity, related_name='numeric_source')
    exam_activity = models.ForeignKey(Activity, null=True, related_name='cal_exam_activity')
    letter_cutoffs = models.CharField(max_length=500, help_text='parsed formula to calculate final letter grade', default='[95, 90, 85, 80, 75, 70, 65, 60, 55, 50]')

    def is_calculated(self):
        return True

    def is_numeric(self):
        return False
    
    LETTERS = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']
    
    class Meta:
        verbose_name_plural = 'cal letter activities'

    def type_long(self):
        return "Calculated Letter Grade"
    
    def get_cutoffs(self):
        """
        Get the list of grade cutoffs: 10 values, lower-bounds for A+, A, A-, B+, ..., as decimal.Decimal
        
        cutoffs = activity.get_cutoffs()
        cutoffs[0] == decimal.Decimal("95")
        """
        return [decimal.Decimal(g) for g in json.loads(self.letter_cutoffs)]

    def set_cutoffs(self, cutoffs):
        """
        Set the grade cutoffs. List must be 10 values, lower-bounds for A+, A, A-, B+, ...
        """
        if len(cutoffs) != 10:
            raise ValueError("Must provide 10 cutoffs.")
        cut_copy = cutoffs[:]
        cut_copy.sort()
        cut_copy.reverse()
        if cutoffs != cut_copy:
            raise ValueError("Cutoffs must be in decending order.")

        self.letter_cutoffs = json.dumps([str(g) for g in cutoffs])
    
    def cutoff_display(self):
        disp = []
        for l,c in zip(self.LETTERS, self.get_cutoffs()):
            disp.append(' <span class="letter">')
            disp.append(l)
            disp.append('</span> ')
            disp.append(str(c))
        disp.append('&nbsp;<span class="letter">F</span> ')

        return mark_safe(''.join(disp))



# list of all subclasses of Activity:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
ACTIVITY_TYPES = [CalNumericActivity, NumericActivity, CalLetterActivity, LetterActivity]

def all_activities_filter(offering, slug=None):
    """
    Return all activities as their most specific class.
    
    This isn't pretty, but it will do the job.
    """
    #key = "all_act_filt" + '_' + offering.slug

    # make sure activity positions are doing okay
    duplicate_pos = Activity.objects.filter(offering=offering).values("position").annotate(count=Count('id')).order_by().filter(count__gt=1)
    if duplicate_pos:
        neaten_activity_positions(offering)

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

    value = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=False)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default='NOGR')
    comment = models.TextField(null=True, max_length=COMMENT_LENGTH)
    
    def __unicode__(self):
        return "Member[%s]'s grade[%s] for [%s]" % (self.member.person.userid, self.value, self.activity)

    @property
    def grade(self):
        "Property for the actual grade received"
        return self.value

    def display_staff(self):
        if self.flag == 'NOGR':
            return '\u2014'
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
            return '\u2014'
        elif self.activity.status == "INVI":
            raise RuntimeError("Can't display invisible grade.")
        elif self.flag == "NOGR":
            return '\u2014'
        elif self.activity.max_grade == 0:
            return '%s/%s' % (self.value, self.activity.max_grade)
        else:
            return '%s/%s (%.2f%%)' % (self.value, self.activity.max_grade, float(self.value)/float(self.activity.max_grade)*100)

    def save(self, entered_by, mark=None, newsitem=True, group=None, is_temporary=False):
        """Save the grade.

        entered_by must be one of:
        (1) the Person object of the person who entered the grade,
        (2) the userid of the person who entered the grade,
        (3) None ONLY if this was a result of a calculation (or for a temporary save that will be re-saved later)

        mark is a reference to the StudentActivityMark or GroupActivity mark, if that's where the grade came from

        newsitem controls the posting of a NewsItem for the student.
        """
        if self.flag == "NOGR":
            # make sure "no grade" values have a zero: just in case the value is used in some other calc
            self.value = 0

        super(NumericGrade, self).save()

        entered_by = get_entry_person(entered_by)
        if bool(mark) and not mark.id:
            raise ValueError("ActivityMark must be saved before calling setMark.")

        if entered_by:
            gh = GradeHistory(activity=self.activity, member=self.member, entered_by=entered_by, activity_status=self.activity.status,
                              numeric_grade=self.value, grade_flag=self.flag, comment=self.comment, mark=mark, group=group)
            gh.save()
        else:
            assert (self.flag == 'CALC') or (is_temporary and self.flag=='NOGR')

        if self.activity.status == "RLS" and newsitem and self.flag not in ["NOGR", "CALC"]:
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name),
                content='A new grade for %s in %s is available.'
                  % (self.activity.name, self.activity.offering.name()),
                url=self.activity.get_absolute_url())
            n.save()

    def get_absolute_url(self):
        """        
        for regular numeric activity return the mark summary page
        but for calculate numeric activity only return the activity information page
        because there is no associated mark summary record
        """
        if CalNumericActivity.objects.filter(id=self.activity.id):
            return reverse("offering:activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        else:
            return reverse("offering:marking:mark_summary_student", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug, 'userid':self.member.person.userid})
    class Meta:
        unique_together = (('activity', 'member'),)


  
class LetterGrade(models.Model):
    """
    Individual letter grade for a LetterActivity
    """
    activity = models.ForeignKey(LetterActivity, null=False)
    member = models.ForeignKey(Member, null=False)
    
    letter_grade = models.CharField(max_length=2, null=False, choices=LETTER_GRADE_CHOICES)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default='NOGR')
    comment = models.TextField(null=True, max_length=COMMENT_LENGTH)
    
    def __unicode__(self):
        return "Member[%s]'s letter grade[%s] for [%s]" % (self.member.person.userid, self.letter_grade, self.activity)

    @property
    def grade(self):
        "Property for the actual grade received"
        return self.letter_grade

    def display_staff(self):
        if self.flag == 'NOGR':
            return '\u2014'
        else:
            return "%s" % (self.letter_grade)
    display_staff_short = display_staff

    def display_with_percentage_student(self):
        """
        Display student grade with percentage from student view, e.g 12/15 (80.00%)
        """
        if self.activity.status == 'URLS':
            return '\u2014'
        elif self.activity.status == "INVI":
            raise RuntimeError("Can't display invisible grade.")
        elif self.flag == "NOGR":
            return '\u2014'
        else:
            return '%s' % (self.letter_grade)
    
    def save(self, entered_by, group=None, newsitem=True):
        """Save the grade.

        entered_by must be one of:
        (1) the Person object of the person who entered the grade,
        (2) the userid of the person who entered the grade,
        (3) None ONLY if this was a result of a calculation

        newsitem controls the posting of a NewsItem for the student.
        """
        super(LetterGrade, self).save()

        entered_by = get_entry_person(entered_by)
        if entered_by:
            gh = GradeHistory(activity=self.activity, member=self.member, entered_by=entered_by, activity_status=self.activity.status,
                              letter_grade=self.letter_grade, grade_flag=self.flag, comment=self.comment, mark=None, group=group)
            gh.save()
        else:
            assert self.flag == 'CALC'

        if self.activity.status=="RLS" and newsitem and self.flag != "NOGR":
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name), 
                content='A new grade for %s in %s is available.' 
                  % (self.activity.name, self.activity.offering.name()),
                url=self.get_absolute_url())
            n.save()

    def get_absolute_url(self):
        """        
        for regular numeric activity return the mark summary page
        but for calculate numeric activity only return the activity information page
        because there is no associated mark summary record
        """
        if CalNumericActivity.objects.filter(id=self.activity.id):
            return reverse("offering:activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        else:
            return reverse("offering:marking:mark_summary_student", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug, 'userid':self.member.person.userid})
            
    class Meta:
        unique_together = (('activity', 'member'), )

NumericActivity.GradeClass = NumericGrade
LetterActivity.GradeClass = LetterGrade

def neaten_activity_positions(course):
    """
    update all positions to consecutive integers: seems possible to get identical positions in some cases
    """
    count = 1
    for a in Activity.objects.filter(offering=course, deleted=False).order_by('position'):
        if a.position != count:
            a.position = count
            a.save()
        count += 1

LETTER_POSITION = {
    'A+': 0,
    'A': 1,
    'A-': 2,
    'B+': 3,
    'B': 4,
    'B-': 5,
    'C+': 6,
    'C': 7,
    'C-': 8,
    'D': 9,
    'F': 11,
    #'FD': 14,
    'N': 13,
    'P': 10,
    #'W': 15,
    #'AE': 17,
    #'AU': 17,
    #'CC': 17,
    #'CF': 17,
    #'CN': 17,
    #'CR': 17,
    #'FX': 17,
    #'WD': 15,
    #'WE': 15,
    'DE': 12,
    'GN': 16,
    'IP': 16
    }
# make sure every possible letter has a sort order
assert set(LETTER_POSITION.keys()) == LETTER_GRADE_CHOICES_IN

# to generate version of LETTER_POSITION in media/js/core.js:
# ./manage.py shell
# from grades.models import *
# import json
# print json.dumps(LETTER_POSITION)

def sorted_letters(grades):
    """
    Sort the collection of grades in a sensible order.  Returns a sorted list.
    
    Decorate-sort-undecorate pattern.
    """
    decorated = [(LETTER_POSITION[g], g) for g in grades]
    decorated.sort()
    return [g for i,g in decorated]

def median_letters(sorted_grades):
    """
    Return a string representing the median of the letter grades.
    """
    l = len(sorted_grades)
    if l == 0:
        return "\u2014"
    elif l%2 == 1:
        return sorted_grades[(l-1)/2]
    else:
        g1 = sorted_grades[l/2-1]      
        g2 = sorted_grades[l/2]
        if g1 == g2:
            return g1
        else:
            # median on a boundary; report as "B/B-"
            return g1 + "/" + g2



def max_letters(sorted_grades):
    """
    Return a string representing the max of the letter grades.
    """
    l = len(sorted_grades)
    if l == 0:
        return "\u2014"
    else:
        return sorted_grades[0]

def min_letters(sorted_grades):
    """
    Return a string representing the min of the letter grades.
    """

    grades_s = [g for g in sorted_grades if LETTER_POSITION[g] <= 11]
    l = len(grades_s)
    if l == 0:
        return "\u2014"
    else:
        return grades_s[l-1]


def get_entry_person(entered_by):
    """
    Take a Person instance or userid and convert to a Person instance (for saving as a GradeHistory.entered_by)
    """
    if isinstance(entered_by, Person):
        return entered_by
    elif entered_by is None:
        return None
    else:
        return Person.objects.get(userid=entered_by)

class GradeHistory(models.Model):
    """
    Grade audit history. Created automatically by ActivityMark.save().
    """
    activity = models.ForeignKey(Activity, null=False)
    member = models.ForeignKey(Member, null=False)
    entered_by = models.ForeignKey(Person, null=False, blank=False)

    activity_status = models.CharField(max_length=4, null=False, choices=ACTIVITY_STATUS_CHOICES, help_text='Activity status when grade was entered.')
    numeric_grade = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=False)
    letter_grade = models.CharField(max_length=2, null=False, choices=LETTER_GRADE_CHOICES)
    grade_flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade')
    comment = models.TextField(null=True, max_length=COMMENT_LENGTH)

    mark = models.ForeignKey('marking.ActivityMark', null=True, help_text='The ActivityMark object this grade came from, if applicable.')
    group = models.ForeignKey('groups.Group', null=True, help_text='If this was a mark for a group, the group.')
    status_change = models.BooleanField(null=False, default=False)

    timestamp = models.DateTimeField(auto_now_add=True)
    #ip = models.GenericIPAddressField() # TODO when we're safely on Django 1.4+?

    class Meta:
        ordering = ['-timestamp']

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it's job is to exist.")

    def grade(self):
        return self.letter_grade or self.numeric_grade 


