import copy
from django.db import models
from django.core.urlresolvers import reverse
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity, NumericGrade
from grades.models import all_activities_filter, neaten_activity_positions
#from submission.models import SubmissionComponent, COMPONENT_TYPES
from coredata.models import Semester
from groups.models import Group, GroupMember
from datetime import datetime
from django.db.models import Q
from submission.models import select_all_components
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
import os.path

MarkingSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

class ActivityComponent(models.Model):
    """    
    Markable Component of a numeric activity   
    """
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
    max_mark = models.DecimalField(max_digits=5, decimal_places=2, null = False)
    title = models.CharField(max_length=30, null = False)
    description = models.TextField(max_length = 200, null = True, blank = True)
    position = models.IntegerField(null = True, default = 0, blank =True)    
    # set this flag if it is deleted by the user
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def __unicode__(self):        
        return self.title
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    class Meta:
        verbose_name_plural = "Activity Marking Components"
        ordering = ['numeric_activity', 'deleted', 'position']
         
class CommonProblem(models.Model):
    """
    Common problem of a activity component. One activity component can have several common problems.
    """
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    title = models.CharField(max_length=30, null = False)
    penalty = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(max_length = 200, null = True, blank = True)
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def __unicode__(self):
        return "common problem %s for %s" % (self.title, self.activity_component)

# 
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
    late_penalty = models.DecimalField(max_digits=5, decimal_places=2, null = True, default = 0, blank = True, help_text='Percentage to deduct from the total mark got due to late submission')
    mark_adjustment = models.DecimalField(max_digits=5, decimal_places=2, null = True, default = 0, blank = True, help_text='Points to deduct for any special reasons')
    mark_adjustment_reason = models.TextField(null = True, max_length = 1000, blank = True)
    file_attachment = models.FileField(storage=MarkingSystemStorage, null = True, upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200)
    created_by = models.CharField(max_length=8, null=False, help_text='Userid who gives the mark')
    created_at = models.DateTimeField(auto_now_add=True)
    # For the purpose of keeping a history,
    # need the copy of the mark here in case that 
    # the 'value' field in the related numeric grades gets overridden
    mark = models.DecimalField(max_digits=5, decimal_places=2)
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
    
    def setMark(self, grade):
        self.mark = grade
    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        path, filename = os.path.split(self.file_attachment.name)
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
      
    def setMark(self, grade):
        """         
        Set the mark
        """
        super(StudentActivityMark, self).setMark(grade)       
        self.numeric_grade.value = grade
        self.numeric_grade.flag = 'GRAD'
        self.numeric_grade.save()            
        
        
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
    
    def setMark(self, grade):
        """         
        Set the mark of the group members
        """
        super(GroupActivityMark, self).setMark(grade)
        #assign mark for each member in the group
        group_members = GroupMember.objects.filter(group=self.group, activity=self.numeric_activity, confirmed=True)
        for g_member in group_members:
            try:            
                ngrade = NumericGrade.objects.get(activity=self.numeric_activity, member=g_member.student)
            except NumericGrade.DoesNotExist: 
                ngrade = NumericGrade(activity=self.numeric_activity, member=g_member.student)
            ngrade.value = grade
            ngrade.flag = 'GRAD'
            ngrade.save()            
            
 
class ActivityComponentMark(models.Model):
    """
    Marking of one particular component of an activity for one student  
    Stores the mark the student gets for the component
    """
    activity_mark = models.ForeignKey(ActivityMark, null = False)    
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    value = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(null = True, max_length=1000, blank=True)
    
    def __unicode__(self):
        # get the student and the activity
        return "Marking for [%s]" %(self.activity_component,)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used for marking history"
        
    class Meta:
        unique_together = (('activity_mark', 'activity_component'),)
        
def get_activity_mark_by_id(activity, student_membership, activity_mark_id): 
     """
     Find the activity_mark with that id if it exists for the student on the activity
     it could be in the StudentActivityMark or GroupActivityMark
     return None if not found.
     """   
    # try StudentActivityMark first 
     try:
         act_mark = StudentActivityMark.objects.select_related().get(id = activity_mark_id)
     except StudentActivityMark.DoesNotExist:
         pass
     else:
         # check consistency against activity and membership
         num_grade = act_mark.numeric_grade 
         if num_grade.activity == activity and num_grade.member == student_membership:
            return act_mark
        
     # not found, then try GroupActivityMark          
     try:
         act_mark = GroupActivityMark.objects.select_related().get(id = activity_mark_id)
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
         act_mark = GroupActivityMark.objects.select_related().get(id = activity_mark_id)
     except GroupActivityMark.DoesNotExist:
         pass
     else:                
         # check consistency with the activity and group_slug
         if act_mark.numeric_activity == activity and act_mark.group == group:
                 return act_mark             
     return None

def get_group_mark(activity, group, include_all = False):
    
    current_mark = None
    all_marks = GroupActivityMark.objects.filter(group = group, numeric_activity = activity)    
    
    if all_marks.count() != 0 : 
        current_mark = all_marks.latest('created_at')
   
    if not include_all:
        return current_mark
    else:
        return {'current_mark': current_mark, 'all_marks': all_marks}


def get_activity_mark_for_student(activity, student_membership, include_all = False):
     """
     Return the mark for the student on the activity.     
     if include_all is False, only return the current mark which was most lately created 
     and thus is currently valid. Otherwise not only return the current mark but also 
     all the history marks for the student on the activity        
     """  
     current_mark = None
     std_marks = None
     grp_marks = None     
     
     # the mark maybe assigned directly to this student 
     num_grade = NumericGrade.objects.get(activity = activity, member = student_membership)
     std_marks = StudentActivityMark.objects.filter(numeric_grade = num_grade)     
     if std_marks.count() != 0 :
        #get the latest one
        current_mark = std_marks.latest('created_at')
        
     # the mark maybe assigned to this student via the group this student participates for this activity       
     group_mems = GroupMember.objects.select_related().filter(student = student_membership, activity = activity, confirmed = True)
     
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
        old_activity = model.objects.get(Q(name=target_activity.name) | Q(short_name=target_activity.short_name, 
                                    deleted = False), 
            offering = target_course_offering)
    except model.DoesNotExist:
        target_activity.save()
    else:    
        old_activity.deleted = True
        old_activity.save()
        target_activity.save()            

def copyCourseSetup(course_copy_from, course_copy_to):
    """
    copy all the activities setup from one course to another
    copy numeric activities with their marking components, common problems and submission components
    """
    #print "copying numeric activities ..."
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
            new_activity_component.save()
            #print "-- marking component %s is copied" % new_activity_component            
            for common_problem in CommonProblem.objects.filter(activity_component=activity_component, deleted=False):
                new_common_problem = copy.deepcopy(common_problem)
                new_common_problem.id = None
                new_common_problem.pk = None
                new_common_problem.penalty = str(new_common_problem.penalty)
                new_common_problem.activity_component = new_activity_component
                new_common_problem.save()
                #print "--- common problem %s is copied" % new_common_problem
        
        for submission_component in select_all_components(activity):
            new_submission_component = copy.deepcopy(submission_component)
            new_submission_component.id = None
            new_submission_component.pk = None
            new_submission_component.activity = new_activity
            new_submission_component.save()
            #print "-- submission component %s is copied" % new_submission_component
        
        #print "- Activity %s is copied" % new_activity
        
        #print "please also copy the calculated letter activities once this type is implemented"    
#    "fixing calculated letter activities ..."
#    for activity in CalLetterActivity.objects.filter(offering = course_copy_to):
#        related_num_act =  activity.numeric_activity
#        related_exam = activity.exam_activity
#        
#        activity.numeric_activity = NumericActivity.objects.get(offering=course_copy_to, name=related_num_act.name)
#        activity.exam_activity = Activity.objects.get(offering=course_copy_to, name=related_exam.name)
#        activity.save()
         
    
