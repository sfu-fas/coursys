import copy
from django.db import models, IntegrityError, transaction
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity, NumericGrade,LetterGrade,LETTER_GRADE_CHOICES
from grades.models import all_activities_filter, neaten_activity_positions, get_entry_person
#from submission.models import SubmissionComponent, COMPONENT_TYPES
from coredata.models import Semester, Member
from groups.models import Group, GroupMember
from datetime import datetime
from django.db.models import Q
from submission.models import select_all_components
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import os, decimal, base64

MarkingSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

class ActivityComponent(models.Model):
    """    
    Markable Component of a numeric activity   
    """
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
    max_mark = models.DecimalField(max_digits=8, decimal_places=2, null = False)
    title = models.CharField(max_length=30, null = False)
    description = models.TextField(max_length = 200, null = True, blank = True)
    position = models.IntegerField(null = True, default = 0, blank =True)    
    # set this flag if it is deleted by the user
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='numeric_activity')
    
    def __unicode__(self):        
        return self.title
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    class Meta:
        verbose_name_plural = "Activity Marking Components"
        ordering = ['numeric_activity', 'deleted', 'position']
    
    def save(self, *args, **kwargs):
        self.slug = None # regerate slug so import format stays in sync
        if self.position == 0:
            others = ActivityComponent.objects.filter(numeric_activity=self.numeric_activity).exclude(pk=self.pk)
            maxpos = others.aggregate(models.Max('position'))['position__max']
            if maxpos:
                self.position = maxpos + 1
            else:
                self.position = 1
        super(ActivityComponent, self).save(*args, **kwargs)
         
class CommonProblem(models.Model):
    """
    Common problem of a activity component. One activity component can have several common problems.
    """
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    title = models.CharField(max_length=30, null = False)
    penalty = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(max_length = 200, null = True, blank = True)
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def __unicode__(self):
        return "common problem %s for %s" % (self.title, self.activity_component)


def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped 
    """
    fullpath = os.path.join(
            instance.activity.offering.slug,
            instance.activity.slug + "_marking",
            datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.created_by),
            filename.encode('ascii', 'ignore'))
    return fullpath 
                
class ActivityMark(models.Model):
    """
    General Marking class for one numeric activity 
    """
    overall_comment = models.TextField(null = True, max_length = 1000, blank = True)
    late_penalty = models.DecimalField(max_digits=5, decimal_places=2, null = True, default = 0, blank = True, help_text='Percentage to deduct from the total due to late submission')
    mark_adjustment = models.DecimalField(max_digits=8, decimal_places=2, null = True, default = 0, blank = True, verbose_name="Mark Penalty", help_text='Points to deduct for any special reasons (may be negative for bonus)')
    mark_adjustment_reason = models.TextField(null = True, max_length = 1000, blank = True, verbose_name="Mark Penalty Reason")
    file_attachment = models.FileField(storage=MarkingSystemStorage, null = True, upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200)
    created_by = models.CharField(max_length=8, null=False, help_text='Userid who gives the mark')
    created_at = models.DateTimeField(auto_now_add=True)
    # For the purpose of keeping a history,
    # need the copy of the mark here in case that 
    # the 'value' field in the related numeric grades gets overridden
    mark = models.DecimalField(max_digits=8, decimal_places=2)
    activity = models.ForeignKey(NumericActivity, null=True) # null=True to keep south happy
    
    def __unicode__(self):
        return "Super object containing additional info for marking"
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    class Meta:
        ordering = ['created_at']
    
    def copyFrom(self, obj):
        """
        Copy information form another ActivityMark object
        """
        self.late_penalty = obj.late_penalty
        self.overall_comment = obj.overall_comment
        self.mark_adjustment = obj.mark_adjustment
        self.mark_adjustment_reason = obj.mark_adjustment_reason
        self.file_attachment = obj.file_attachment
    
    def mark_adjustment_neg(self):
        return -self.mark_adjustment
    def setMark(self, grade):
        self.mark = grade
        if not self.id:
            # ActivityMark must be saved before we can create GradeHistory objects: that is done in [subclasses].save()
            self.save()
        
    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        _, filename = os.path.split(self.file_attachment.name)
        return filename

class StudentActivityMark(ActivityMark):
    """
    Marking of one student on one numeric activity 
    """        
    numeric_grade = models.ForeignKey(NumericGrade, null = False)
       
    def __unicode__(self):
        # get the student and the activity
        student = self.numeric_grade.member.person
        activity = self.numeric_grade.activity      
        return "Marking for student [%s] for activity [%s]" %(student, activity)   
    def get_absolute_url(self):
        return reverse('marking.views.mark_history_student', kwargs={'course_slug': self.numeric_grade.activity.offering.slug, 'activity_slug': self.numeric_grade.activity.slug, 'userid': self.numeric_grade.member.person.userid})
      
    def setMark(self, grade, entered_by):
        """         
        Set the mark
        """
        super(StudentActivityMark, self).setMark(grade)       
        self.numeric_grade.value = grade
        self.numeric_grade.flag = 'GRAD'
        self.numeric_grade.save(entered_by=entered_by, mark=self)            
        
        
class GroupActivityMark(ActivityMark):
    """
    Marking of one group on one numeric activity
    """
    group = models.ForeignKey(Group, null = False) 
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
         
    def __unicode__(self):
        return "Marking for group [%s] for activity [%s]" %(self.group, self.numeric_activity)
    def get_absolute_url(self):
        return reverse('marking.views.mark_history_group', kwargs={'course_slug': self.numeric_activity.offering.slug, 'activity_slug': self.numeric_activity.slug, 'group_slug': self.group.slug})
    
    def setMark(self, grade, entered_by, details=True):
        """         
        Set the mark of the group members
        """
        super(GroupActivityMark, self).setMark(grade)
        #assign mark for each member in the group
        group_members = GroupMember.objects.filter(group=self.group, activity=self.numeric_activity, confirmed=True)
        entered_by = get_entry_person(entered_by)
        for g_member in group_members:
            try:            
                ngrade = NumericGrade.objects.get(activity=self.numeric_activity, member=g_member.student)
            except NumericGrade.DoesNotExist: 
                ngrade = NumericGrade(activity=self.numeric_activity, member=g_member.student)
            ngrade.value = grade
            ngrade.flag = 'GRAD'
            if details:
                ngrade.save(entered_by=entered_by, mark=self, group=self.group)
            else:
                # this is just a placeholder for a number-only mark
                ngrade.save(entered_by=entered_by, mark=None, group=self.group)
            
 
class ActivityComponentMark(models.Model):
    """
    Marking of one particular component of an activity for one student  
    Stores the mark the student gets for the component
    """
    activity_mark = models.ForeignKey(ActivityMark, null = False)    
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    value = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Mark')
    comment = models.TextField(null = True, max_length=1000, blank=True)
    
    def __unicode__(self):
        # get the student and the activity
        return "Marking for [%s]" %(self.activity_component,)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used for marking history"
        
    class Meta:
        unique_together = (('activity_mark', 'activity_component'),)
        ordering = ('activity_component',)


class ActivityMark_LetterGrade(models.Model):
    """
    General Marking class for one letter activity 
    """
    overall_comment = models.TextField(null = True, max_length = 1000, blank = True)
    created_by = models.CharField(max_length=8, null=False, help_text='Userid who gives the mark')
    created_at = models.DateTimeField(auto_now_add=True)
    # For the purpose of keeping a history,
    # need the copy of the mark here in case that 
    # the 'value' field in the related numeric grades gets overridden
    mark = models.CharField(max_length=2, null=False,choices=LETTER_GRADE_CHOICES)
    activity = models.ForeignKey(LetterActivity, null=True) # null=True to keep south happy
    
    def __unicode__(self):
        return "Super object containing additional info for marking"
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    class Meta:
        ordering = ['created_at']
    
    def copyFrom(self, obj):
        """
        Copy information form another ActivityMark object
        """
        self.overall_comment = obj.overall_comment
        self.file_attachment = obj.file_attachment
    
    def setMark(self, grade):
        self.mark = grade
    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        path, filename = os.path.split(self.file_attachment.name)
        return filename

class StudentActivityMark_LetterGrade(ActivityMark_LetterGrade):
    """
    Marking of one student on one letter activity 
    """        
    letter_grade = models.ForeignKey(LetterGrade, null = False, choices=LETTER_GRADE_CHOICES)
       
    def __unicode__(self):
        # get the student and the activity
        student = self.letter_grade.member.person
        activity = self.letter_grade.activity      
        return "Marking for student [%s] for activity [%s]" %(student, activity)   
    def get_absolute_url(self):
        return reverse('marking.views.mark_history_student', kwargs={'course_slug': self.letter_grade.activity.offering.slug, 'activity_slug': self.letter_grade.activity.slug, 'userid': self.letter_grade.member.person.userid})
      
    def setMark(self, grade, entered_by):
        """
        Set the mark
        """
        super(StudentActivityMark, self).setMark(grade)       
        self.letter_grade.value = grade
        self.letter_grade.flag = 'GRAD'
        self.letter_grade.save(entered_by=entered_by, mark=self)   

class GroupActivityMark_LetterGrade(ActivityMark_LetterGrade):
    """
    Marking of one group on one letter activity
    """
    group = models.ForeignKey(Group, null = False) 
    letter_activity = models.ForeignKey(LetterActivity, null = False)
    #letter_grade = models.ForeignKey(LetterGrade, null = False, choices=LETTER_GRADE_CHOICES)
    letter_grade = models.CharField(max_length=2, choices=LETTER_GRADE_CHOICES)
         
    def __unicode__(self):
        return "Marking for group [%s] for activity [%s]" %(self.group, self.letter_activity)
    def get_absolute_url(self):
        return reverse('marking.views.mark_history_group', kwargs={'course_slug': self.letter_activity.offering.slug, 'activity_slug': self.letter_activity.slug, 'group_slug': self.group.slug})
    
    def setMark(self, grade, entered_by):
        """         
        Set the mark of the group members
        """
        super(GroupActivityMark_LetterGrade, self).setMark(grade)
        #assign mark for each member in the group
        group_members = GroupMember.objects.filter(group=self.group, activity=self.letter_activity, confirmed=True)
        for g_member in group_members:
            try:            
                lgrade = LetterGrade.objects.get(activity=self.letter_activity, member=g_member.student)
            except LetterGrade.DoesNotExist: 
                lgrade = LetterGrade(activity=self.letter_activity, member=g_member.student)
            lgrade.letter_grade = grade
            lgrade.flag = 'GRAD'
            lgrade.save(entered_by=entered_by, group=self.group)

       
def get_activity_mark_by_id(activity, student_membership, activity_mark_id): 
    """
    Find the activity_mark with that id if it exists for the student on the activity
    it could be in the StudentActivityMark or GroupActivityMark
    return None if not found.
    """   
    # try StudentActivityMark first 
    try:
        act_mark = StudentActivityMark.objects.get(id=activity_mark_id)
    except StudentActivityMark.DoesNotExist:
        pass
    else:
        # check consistency against activity and membership
        num_grade = act_mark.numeric_grade 
        if num_grade.activity == activity and num_grade.member == student_membership:
            return act_mark
        
    # not found, then try GroupActivityMark
    try:
        act_mark = GroupActivityMark.objects.get(id = activity_mark_id)
    except GroupActivityMark.DoesNotExist:
        pass
    else:                
        # check consistency with the activity and membership
        if act_mark.numeric_activity == activity:
            group = act_mark.group
            try:
                group_mem = GroupMember.objects.get(group = group, activity = activity, student = student_membership, confirmed = True)
            except GroupMember.DoesNotExist:
                pass
            else:
                return act_mark         
    
    return None
 
def get_group_mark_by_id(activity, group, activity_mark_id): 
     """
     Find the activity_mark with that id if it exists for the group on the activity
     return None if not found.
     """
     try:
         act_mark = GroupActivityMark.objects.get(id = activity_mark_id)
     except GroupActivityMark.DoesNotExist:
         pass
     else:                
         # check consistency with the activity and group_slug
         if act_mark.numeric_activity == activity and act_mark.group == group:
                 return act_mark             
     return None

def get_group_mark(activity, group, include_all = False):
    
    current_mark = None
    if isinstance(activity, LetterActivity):
        all_marks = GroupActivityMark_LetterGrade.objects.filter(group=group, letter_activity=activity)
    else:
        all_marks = GroupActivityMark.objects.filter(group=group, numeric_activity=activity)
    
    if all_marks.count() != 0: 
        current_mark = all_marks.latest('created_at')
   
    if not include_all:
        return current_mark
    else:
        return {'current_mark': current_mark, 'all_marks': all_marks}


def get_activity_mark_for_student(activity, student_membership, include_all=False):
    """
    Return the mark for the student on the activity.
    if include_all is False, only return the current mark which was most lately created
    and thus is currently valid. Otherwise not only return the current mark but also
    all the history marks for the student on the activity
    """  
    current_mark = None
    grp_marks = None     
    
    # the mark maybe assigned directly to this student 
    try:
        num_grade = NumericGrade.objects.get(activity=activity, member=student_membership)
    except NumericGrade.DoesNotExist:
        return None
    std_marks = StudentActivityMark.objects.filter(numeric_grade = num_grade)     
    if std_marks.count() != 0 :
        #get the latest one
        current_mark = std_marks.latest('created_at')
        
    # the mark maybe assigned to this student via the group this student participates for this activity       
    group_mems = GroupMember.objects.filter(student=student_membership, activity=activity, confirmed=True).select_related('group')
    
    if group_mems.count() > 0:
        group = group_mems[0].group # there should be only one group this student is in
        grp_mark_info = get_group_mark(activity, group, True)        
        latest_grp_mark = grp_mark_info['current_mark']
        grp_marks = grp_mark_info['all_marks']
        
        if (current_mark  == None) or \
           (latest_grp_mark != None and latest_grp_mark.created_at > current_mark.created_at):
            current_mark = latest_grp_mark
        
    if not include_all:
        return current_mark
    else:
        return {'current_mark' : current_mark, 
                'marks_individual' : std_marks,
                'marks_via_group' : grp_marks}

def copy_activity(source_activity, source_course_offering, target_course_offering):
    new_activity = copy.deepcopy(source_activity)
    new_activity.id = None
    new_activity.pk = None
    new_activity.activity_ptr_id = None
    new_activity.slug = None
    if hasattr(new_activity, 'numericactivity_ptr_id'):
        new_activity.numericactivity_ptr_id = None
    if hasattr(new_activity, 'letteractivity_ptr_id'):
        new_activity.letteractivity_ptr_id = None

    if source_activity.status=="INVI":
        new_activity.status = 'INVI'        
    else:
        new_activity.status = 'URLS'

    new_activity.offering = target_course_offering

    if source_activity.due_date != None:
        week, wkday = source_course_offering.semester.week_weekday(source_activity.due_date)
        new_due_date = target_course_offering.semester.duedate(week, wkday, source_activity.due_date)
        new_activity.due_date = new_due_date
    return new_activity

def save_copied_activity(target_activity, model, target_course_offering):
    """
    to ensure the uniqueness of name and short name of activities, 
    we have to resolve the conflicts by deleting the old activity that conflicts with the new one
    """
    try:
        old_activity = model.objects.get(Q(name=target_activity.name) | 
                                         Q(short_name=target_activity.short_name, deleted = False), 
                                        offering=target_course_offering, deleted=False)
    except model.DoesNotExist:
        target_activity.save(force_insert=True)
    else:    
        old_activity.deleted = True
        old_activity.save()
        target_activity.save(force_insert=True)            

@transaction.atomic
def copyCourseSetup(course_copy_from, course_copy_to):
    """
    copy all the activities setup from one course to another
    copy numeric activities with their marking components, common problems and submission components
    """
    from submission.models.code import CodeComponent
    from submission.models.codefile import CodefileComponent
    # copy things in offering's .config dict
    for f in course_copy_from.copy_config_fields:
        if f in course_copy_from.config:
            course_copy_to.config[f] = course_copy_from.config[f]
    course_copy_to.save()

    # copy Activities (and related content)
    all_activities = all_activities_filter(offering=course_copy_from)

    for activity in all_activities:
        Class = activity.__class__
        new_activity = copy_activity(activity, course_copy_from, course_copy_to)
        save_copied_activity(new_activity, Class, course_copy_to)
    
        # should only apply to NumericActivity: others have no ActivityComponents
        for activity_component in ActivityComponent.objects.filter(numeric_activity=activity, deleted=False):
            new_activity_component = copy.deepcopy(activity_component)
            new_activity_component.id = None
            new_activity_component.pk = None
            new_activity_component.numeric_activity = new_activity
            new_activity_component.slug = None
            new_activity_component.save(force_insert=True)
            for common_problem in CommonProblem.objects.filter(activity_component=activity_component, deleted=False):
                new_common_problem = copy.deepcopy(common_problem)
                new_common_problem.id = None
                new_common_problem.pk = None
                new_common_problem.penalty = str(new_common_problem.penalty)
                new_common_problem.activity_component = new_activity_component
                new_common_problem.save(force_insert=True)
        
        for submission_component in select_all_components(activity):
            new_submission_component = copy.deepcopy(submission_component)
            new_submission_component.id = None
            new_submission_component.pk = None
            new_submission_component.activity = new_activity
            new_submission_component.slug = None
            if isinstance(new_submission_component, CodeComponent):
                # upgrade Code to Codefile while migrating
                new_submission_component = CodefileComponent.build_from_codecomponent(new_submission_component)
            new_submission_component.save(force_insert=True)
    
    for activity in CalLetterActivity.objects.filter(offering=course_copy_to):
        # fix up source and exam activities as best possible
        if activity.numeric_activity:
            try:
                na = NumericActivity.objects.get(offering=course_copy_to, name=activity.numeric_activity.name, deleted=False)
            except NumericActivity.DoesNotExist:
                na = NumericActivity.objects.filter(offering=course_copy_to, deleted=False)[0]
            activity.numeric_activity = na
            
        if activity.exam_activity:
            try:
                a = Activity.objects.get(offering=course_copy_to, name=activity.exam_activity.name, deleted=False)
            except Activity.DoesNotExist:
                a = Activity.objects.filter(offering=course_copy_to, deleted=False)[0]
            activity.exam_activity = a
        
        activity.save()
    
    
    # copy the Pages
    from pages.models import Page, PageFilesStorage, attachment_upload_to
    for p in Page.objects.filter(offering=course_copy_from):
        new_p = copy.deepcopy(p)
        new_p.id = None
        new_p.pk = None
        new_p.offering = course_copy_to
        while True:
            count = 0
            orig_label = new_p.label
            try:
                new_p.save(force_insert=True)
                break
            except IntegrityError:
                count += 1
                new_p.label = orig_label + "-" + str(count)
        
        # if there are release dates, adapt to new semester
        if new_p.releasedate():
            week, wkday = course_copy_from.semester.week_weekday(new_p.releasedate())
            new_date = course_copy_to.semester.duedate(week, wkday, None)
            new_p.set_releasedate(new_date)
        if new_p.editdate():
            week, wkday = course_copy_from.semester.week_weekday(new_p.editdate())
            new_date = course_copy_to.semester.duedate(week, wkday, None)
            new_p.set_editdate(new_date)
        
        v = p.current_version()
        new_v = copy.deepcopy(v)
        new_v.id = None
        new_v.pk = None
        new_v.page = new_p
        # collapse old version history
        new_v.wikitext = v.get_wikitext()
        new_v.diff = None
        new_v.diff_from = None
        new_v.comment = "Page migrated from %s" % (course_copy_from)
        
        if new_v.file_attachment:
            # copy the file (so we can safely remove old semesters'
            # files without leaving bad path reference)
            src = v.file_attachment.path
            path = attachment_upload_to(new_v, new_v.file_name)
            dst = PageFilesStorage.path(path)
            dstpath, dstfile = os.path.split(dst)
            while os.path.exists(os.path.join(dstpath, dstfile)):
                # handle duplicates by mangling the directory name
                dstpath += "_"
            dst = os.path.join(dstpath, dstfile)
            new_v.file_attachment = dst
            
            if not os.path.exists(dstpath):
                os.makedirs(dstpath)

            try:
                os.link(src, dst)
            except:
                # any problems with the hardlink: try simple copy
                import shutil
                shutil.copyfile(src, dst)

        new_v.save(force_insert=True)



from django.forms import ValidationError
def activity_marks_from_JSON(activity, userid, data):
    """
    Build ActivityMark and ActivityComponentMark objects from imported JSON data.
    
    Return three lists: all ActivityMarks and all ActivityComponentMark and all NumericGrades *all not yet saved*.
    """
    if not isinstance(data, dict):
        raise ValidationError(u'Outer JSON data structure must be an object.')
    if 'marks' not in data:
        raise ValidationError(u'Outer JSON data object must contain key "marks".')
    if not isinstance(data['marks'], list):
        raise ValidationError(u'Value for "marks" must be a list.')

    # All the ActivityMark and ActivityComponentMark objects get built here:
    # we basically have to do this work to validate anyway.
    components = ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)
    components = dict((ac.slug, ac) for ac in components)
    activity_marks = []
    activity_component_marks = []
    numeric_grades = []
    found = set()
    combine = False # are we combining these marks with existing (as opposed to overwriting)?
    if 'combine' in data and bool(data['combine']):
        combine = True

    for markdata in data['marks']:
        if not isinstance(markdata, dict):
            raise ValidationError(u'Elements of array must be JSON objects.')

        # build the ActivityMark object and populate as much as possible for now.
        if activity.group and 'group' in markdata:
            # GroupActivityMark
            try:
                group = Group.objects.get(slug=markdata['group'], courseoffering=activity.offering)
            except Group.DoesNotExist:
                raise ValidationError(u'Group with id "%s" not found.' % (markdata['group']))
            am = GroupActivityMark(activity=activity, numeric_activity=activity, group=group, created_by=userid)
            recordid = markdata['group']

        elif 'userid' in markdata:
            # StudentActivityMark
            try:
                member = Member.objects.get(person__userid=markdata['userid'], offering=activity.offering, role="STUD")
            except Member.DoesNotExist:
                raise ValidationError(u'Userid %s not in course.' % (markdata['userid']))
            am = StudentActivityMark(activity=activity, created_by=userid)
            recordid = markdata['userid']
        else:
            raise ValidationError(u'Must specify "userid" or "group" for mark.')

        # check for duplicates in import
        if recordid in found:
            raise ValidationError(u'Duplicate marks for "%s".' % (recordid))
        found.add(recordid)

        if combine:
            # if we're being asked to combine with old marks, get the old one (if exists)
            try:
                if activity.group:
                    old_am = get_group_mark(activity, group)
                else:
                    old_am = get_activity_mark_for_student(activity, member)
            except NumericGrade.DoesNotExist:
                old_am = None

        activity_marks.append(am)

        # build ActivityComponentMarks
        found_comp_slugs = set()
        mark_total = 0
        late_percent = decimal.Decimal(0)
        mark_penalty = decimal.Decimal(0)
        mark_penalty_reason = ""
        overall_comment = ""
        file_filename = None
        file_data = None
        file_mediatype = None

        if combine and old_am:
            late_percent = old_am.late_penalty
            mark_penalty = old_am.mark_adjustment
            mark_penalty_reason = old_am.mark_adjustment_reason
            overall_comment = old_am.overall_comment

        for slug in markdata:
            # handle special-case slugs (that don't represent MarkComponents)
            if slug in ['userid', 'group']:
                continue
            elif slug=="late_percent":
                try:
                    late_percent = decimal.Decimal(str(markdata[slug]))
                except decimal.InvalidOperation:
                    raise ValidationError(u'Value for "late_percent" must be numeric in record for "%s".' % (recordid))
                continue
            elif slug=="mark_penalty":
                try:
                    mark_penalty = decimal.Decimal(str(markdata[slug]))
                except decimal.InvalidOperation:
                    raise ValidationError(u'Value for "mark_penalty" must be numeric in record for "%s".' % (recordid))
                continue
            elif slug=="mark_penalty_reason":
                mark_penalty_reason = unicode(markdata[slug])
                continue
            elif slug=="overall_comment":
                overall_comment = unicode(markdata[slug])
                continue
            elif slug=="attach_type":
                file_mediatype = str(markdata[slug])
                continue
            elif slug=="attach_filename":
                file_filename = unicode(markdata[slug])
                continue
            elif slug=="attach_data":
                try:
                    file_data = base64.b64decode(markdata[slug])
                except TypeError:
                    raise ValidationError('Invalid base64 file data for "%s"' % (recordid))
                continue
            
            # handle MarkComponents
            if slug in components and slug not in found_comp_slugs:
                comp = components[slug]
                found_comp_slugs.add(slug)
            elif slug in components:
                # shouldn't happend because JSON lib forces unique keys, but let's be extra safe...
                raise ValidationError(u'Multiple values given for "%s" in record for "%s".' % (slug, recordid))
            else:
                raise ValidationError(u'Mark component "%s" not found in record for "%s".' % (slug, recordid))

            cm = ActivityComponentMark(activity_mark=am, activity_component=comp)
            activity_component_marks.append(cm)

            componentdata = markdata[slug]
            if not isinstance(componentdata, dict):
                raise ValidationError(u'Mark component data must be JSON object (in "%s" for "%s").' % (slug, recordid))

            if 'mark' not in componentdata:
                raise ValidationError(u'Must give "mark" for "%s" in record for "%s".' % (comp.title, recordid))
            
            try:
                value = decimal.Decimal(str(componentdata['mark']))
            except decimal.InvalidOperation:
                raise ValidationError(u'Value for "mark" must be numeric for "%s" in record for "%s".' % (comp.title, recordid))

            cm.value = value
            mark_total += float(componentdata['mark'])
            if 'comment' in componentdata:
                cm.comment = unicode(componentdata['comment'])

        for slug in set(components.keys()) - found_comp_slugs:
            # handle missing components
            cm = ActivityComponentMark(activity_mark=am, activity_component=components[slug])
            activity_component_marks.append(cm)
            if combine and old_am:
                old_cm = ActivityComponentMark.objects.get(activity_mark=old_am, activity_component=components[slug])
                cm.value = old_cm.value
                cm.comment = old_cm.comment
                mark_total += float(cm.value)
            else:                
                cm.value = decimal.Decimal(0)
                cm.comment = ''

        # handle file attachment
        if file_filename or file_data or file_mediatype:
            # new attachment
            if not (file_filename and file_data and file_mediatype):
                raise ValidationError(u'Must specify all or none of "attach_type", "attach_filename", "attach_data" in record for "%s"' % (recordid))
            am.file_attachment.save(name=file_filename, content=ContentFile(file_data), save=False)
            am.file_mediatype = file_mediatype
        elif combine and old_am:
            # recycle old
            am.file_attachment = old_am.file_attachment
            am.file_mediatype = old_am.file_mediatype
        else:
            # none
            am.file_attachment = None
            am.file_mediatype = None
        
        am.late_penalty = late_percent
        am.mark_adjustment = mark_penalty
        am.mark_adjustment_reason = mark_penalty_reason
        am.overall_comment = overall_comment
        
        mark_total = (1-late_percent/decimal.Decimal(100)) * \
                  (decimal.Decimal(str(mark_total)) - mark_penalty)
        
        # put the total mark and numeric grade objects in place
        am.mark = mark_total
        value = mark_total
        if isinstance(am, StudentActivityMark):
            grades = NumericGrade.objects.filter(activity=activity, member=member)
            if grades:
                numeric_grade = grades[0]
                numeric_grade.flag = "GRAD"
            else:
                numeric_grade = NumericGrade(activity=activity, member=member, flag="GRAD")

            numeric_grade.value = value
            am.numeric_grade = numeric_grade
            numeric_grades.append(numeric_grade)

        else:
            group_members = GroupMember.objects.filter(group=group, activity=activity, confirmed=True)
            for g_member in group_members:
                try:            
                    ngrade = NumericGrade.objects.get(activity=activity, member=g_member.student)
                except NumericGrade.DoesNotExist: 
                    ngrade = NumericGrade(activity=activity, member=g_member.student)
                ngrade.value = value
                ngrade.flag = 'GRAD'
                numeric_grades.append(ngrade)

    return (activity_marks, activity_component_marks, numeric_grades)

