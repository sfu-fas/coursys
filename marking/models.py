from django.db import models
from grades.models import NumericActivity, NumericGrade 

class ActivityComponent(models.Model):
    """    
    Markable Component of a numeric activity   
    """
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
    max_mark = models.DecimalField(max_digits=5, decimal_places=2, null = False)
    title = models.CharField(max_length=30, null = False)
    description = models.CharField(max_length = 200, null = True, blank = True)
    
    # set this flag if it is deleted by the user
    deleted = models.BooleanField(null = False, default = False)
    def __unicode__(self):
        return "component %s for %s" % (self.title, self.numeric_activity)
    #class Meta:
     #   unique_together = (('numeric_activity', 'title'),)
     
class CommonProblem(models.Model):
    """
    Common problem of a activity component. One activity component can have several common problems.
    """
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    title = models.CharField(max_length=30, null = False)
    penalty = models.IntegerField(null = True, default = 0, blank = True)
    description = models.TextField(null = True, max_length = 1000, blank = True)
    def __unicode__(self):
        return "common problem %s for %s" % (self.title, self.activity_component)
     
class ActivityMark(models.Model):
    """
    General Marking class for one numeric activity 
    """    
    overall_comment = models.TextField(null = True, max_length = 1000, blank = True)
    late_penalty = models.IntegerField(null = True, default = 0, blank = True)
    mark_adjustment = models.IntegerField(null = True, default = 0, blank = True)
    mark_adjustment_reason = models.TextField(null = True, max_length = 1000, blank = True)
    file_attachment = models.FileField(null = True, upload_to = "student&group/files/%Y %m %d %H:%M:%S'", blank=True)#TODO: need to add student name or group name to the path  
     
    #def __unicode__(self):
        # get the activity
        #activity = self.numeric_grade.typed_activity #Can the base class use numeric_grade from derived class?     
        #return "Marking for for activity [%s]" %(activity,)

class StudentActivityMark(ActivityMark):
    """
    Marking of one student on one numeric activity 
    """        
    numeric_grade = models.OneToOneField(NumericGrade, null = False)
    
    def __unicode__(self):
        # get the student and the activity
        student = self.numeric_grade.member.person
        activity = self.numeric_grade.typed_activity      
        return "Marking for [%s] for activity [%s]" %(student, activity)

    def setMark(self, grade):
        """         
        Set the mark
e       """
        self.numeric_grade.value = grade
        self.numeric_grade.flag = 'GRAD'
        self.numeric_grade.save()            
        
        
class GroupActivityMark(ActivityMark):
    """
    Marking of one group on one numeric activity
    """
    group = None #TODO:change to ForeignKey(Group.group object, null = False)
    grade = models.DecimalField(max_digits=5, decimal_places=2)
    def __unicode__(self):
        return "Marking for [%s] for activity [%s]" %(self.group,)#TODO: need some way to find the activity
    
    def setMark(self, grade, status_flag):
        #set mark for each of the student in the group
        self.grade = grade
 
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
        student = self.activity_mark.numeric_grade.member.person
        return "Marking for [%s]" %(self.activity_component,)
        
    class Meta:
        unique_together = (('activity_mark', 'activity_component'),)

from django.forms import ModelForm
class ActivityComponentMarkForm(ModelForm):
    class Meta:
        model = ActivityComponentMark            
        fields = ['comment', 'value']
        exclude = ['activity_mark', 'activity_component']
    
    
