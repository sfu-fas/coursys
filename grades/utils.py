"""
This module collects classes and functions that are for the display purpose of Grades component
"""

from grades.models import Activity, NumericActivity, LetterActivity, NumericGrade, \
                           LetterGrade, all_activities_filter, ACTIVITY_TYPES, FLAGS
from coredata.models import CourseOffering, Person
import math
import decimal

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}
_NO_GRADE = '--'
_DECIMAL_PLACE = 2

#class CourseInfo:
#    """
#    Object holding course info for the display
#    """
#    def __init__(self, subject, number, section, semester, title, campus, instructor_list, ta_list, grade_approver_list, number_of_students):
#        self.subject = subject
#        self.number = number
#        self.section = section
#        self.semester = semester
#        self.title = title
#        self.campus = campus
#        self.instructor_list = instructor_list
#        self.ta_list = ta_list
#        self.grade_approver_list = grade_approver_list
#        self.number_of_students = number_of_students
        
class ActivityStat:
    """
    Object holding activity stat info for the display
    """
    def __init__(self, average, min, max, median, stddev):
        self.average = average
        self.min = min
        self.max = max
        self.median = median
        self.stddev = stddev
        
class StudentActivityInfo:
    """
    Object holding student activity info for the display
    """
    def __init__(self, id, name, userid, emplid, email, activity, grade_status, numeric_grade, letter_grade):
        self.id = id
        self.name = name
        self.userid = userid
        self.emplid = emplid
        self.email = email
        self.activity = activity
        self.grade_status = grade_status
        self.numeric_grade = numeric_grade
        self.letter_grade = letter_grade
        
    def display_grade_student(self):
        if self.activity.status == 'URLS':
            return _NO_GRADE
        elif self.activity.status=="INVI":
            raise RuntimeError, "Can't display invisible grade."
        else:
            if self.grade_status == FLAGS['NOGR']:
                return _NO_GRADE
            else:
                if isinstance(self.activity, NumericActivity):
                    return '%s/%s' % (self.numeric_grade, self.activity.max_grade)
                elif isinstance(self.activity, LetterActivity):
                    return self.letter_grade
    
    def display_grade_staff(self):
        if self.grade_status == FLAGS['NOGR']:
            return _NO_GRADE
        else:
            if isinstance(self.activity, NumericActivity):
                return '%s/%s' % (self.numeric_grade, self.activity.max_grade)
            elif isinstance(self.activity, LetterActivity):
                return self.letter_grade
    
    def append_activity_stat(self):
        if isinstance(self.activity, NumericActivity):
            self.activity_stat = fetch_numeric_activity_stat(self.activity)
        else:
            self.activity_stat = None
            
        return self
        
        
def reorder_course_activities(ordered_activities, activity_slug, order):
    """
    Reorder the activity in the Activity list of a course according to the
    specified order action. Please make sure the Activity list belongs to
    the same course.
    """
    for activity in ordered_activities:
        if not isinstance(activity, Activity):
            return
    for i in range(0, len(ordered_activities)):
        if ordered_activities[i].slug == activity_slug:
            if (order == ORDER_TYPE['UP']) and (not i == 0):
                # swap position
                temp = ordered_activities[i-1].position
                ordered_activities[i-1].position = ordered_activities[i].position
                ordered_activities[i].position = temp
                ordered_activities[i-1].save()
                ordered_activities[i].save()
            elif (order == ORDER_TYPE['DN']) and (not i == len(ordered_activities) - 1):
                # swap position
                temp = ordered_activities[i+1].position
                ordered_activities[i+1].position = ordered_activities[i].position
                ordered_activities[i].position = temp
                ordered_activities[i+1].save()
                ordered_activities[i].save()
            break

def create_StudentActivityInfo_list(course, activity, student=None):
    """
    Return a StudentGradeInfo list which either contains all the enrolled students'
    grade information in a course activity when student is not specified, or contains
    the specified student's grade information in a course activity
    """
    if not course or not activity:
        return
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    if not isinstance(course, CourseOffering):
        return
    # verify if the course contains the activity
    if not all_activities_filter(slug=activity.slug, offering=course):
        return
    if not student:
        student_list = course.members.filter(person__role='STUD')
    else:
        if not isinstance(student, Person):
            return
        student_list = [student]
    student_activity_info_list = []
    
    if isinstance(activity, NumericActivity):
        numeric_grade_list = NumericGrade.objects.filter(activity=activity)
        for student in student_list:
            student_grade_status = None
            for numeric_grade in numeric_grade_list:
                if numeric_grade.member.person == student:
                    student_grade_status = numeric_grade.get_flag_display()
                    student_grade = numeric_grade.value
                    break
            if not student_grade_status:
                student_grade_status = FLAGS['NOGR']
                student_grade = None
            student_activity_info_list.append(StudentActivityInfo(student.id, student.name(), student.userid, student.emplid, student.email(),
                                                            activity, student_grade_status, student_grade, None))
    elif isinstance(activity, LetterActivity):
        letter_grade_list = LetterGrade.objects.filter(activity=activity)
        for student in student_list:
            student_grade_status = None
            for letter_grade in letter_grade_list:
                if letter_grade.member.person == student:
                    student_grade_status = letter_grade.get_flag_display()
                    student_grade = letter_grade.letter_grade
                    break
            if not student_grade_status:
                student_grade_status = FLAGS['NOGR']
                student_grade = None
            student_activity_info_list.append(StudentActivityInfo(student.id, student.name(), student.userid, student.emplid, student.email(),
                                                            activity, student_grade_status, None, student_grade))
    return student_activity_info_list

def fetch_numeric_activity_stat(activity):
    student_list = activity.offering.members.filter(person__role='STUD')
    numeric_grade_list = NumericGrade.objects.filter(activity=activity)\
                        .select_related('member','member__person')
    
    student_grade_list = []
    for student in student_list:
        student_found = False
        for numeric_grade in numeric_grade_list:
            if numeric_grade.member.person == student:
                student_found = True
                if numeric_grade.flag == 'GRAD':
                    student_grade_list.append(numeric_grade.value)
                else:
                    student_grade_list.append(0)
                break
        if not student_found:
            student_grade_list.append(0)
    student_grade_list.sort()
    student_grade_list_count = len(student_grade_list)
    average = sum(student_grade_list)
    average = float(average) / student_grade_list_count
    stddev = math.sqrt(sum([(float(student_grade) - average) ** 2 for student_grade in student_grade_list]) / student_grade_list_count)
    
    return ActivityStat(format_number(average, _DECIMAL_PLACE), format_number(student_grade_list[0], _DECIMAL_PLACE),
                        format_number(student_grade_list[student_grade_list_count - 1], _DECIMAL_PLACE),
                        format_number(student_grade_list[(student_grade_list_count - 1) / 2], _DECIMAL_PLACE),
                        format_number(stddev, _DECIMAL_PLACE))
    
def format_number(value, decimal_places):
    """
    Formats a number into a string with the requisite number of decimal places.
    """
    if isinstance(value, decimal.Decimal):
        context = decimal.getcontext().copy()
        return u'%s' % str(value.quantize(decimal.Decimal(".1") ** decimal_places, context=context))
    else:
        return u"%.*f" % (decimal_places, value)
