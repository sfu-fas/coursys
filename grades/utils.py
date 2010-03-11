"""
This module collects classes and functions that are for the display purpose of Grades component
"""

from grades.models import Activity, NumericActivity, LetterActivity, NumericGrade, \
                           LetterGrade, all_activities_filter, ACTIVITY_TYPES, FLAGS
from coredata.models import CourseOffering, Person

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}

class CourseInfo:
    """
    Object holding course info for the display in 'course' page 
    """
    def __init__(self, subject, number, section, semester, title, campus, instructor_list, ta_list, grade_approver_list, number_of_students):
        self.subject = subject
        self.number = number
        self.section = section
        self.semester = semester
        self.title = title
        self.campus = campus
        self.instructor_list = instructor_list
        self.ta_list = ta_list
        self.grade_approver_list = grade_approver_list
        self.number_of_students = number_of_students
        
class StudentGradeInfo:
    """
    Object holding student grade info for the display in 'activity_info' page 
    """
    def __init__(self, id, name, userid, emplid, email, grade_status, grade):
        self.id = id
        self.name = name
        self.userid = userid
        self.emplid = emplid
        self.email = email
        self.grade_status = grade_status
        self.grade = grade
        
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

def create_StudentGradeInfo_list(course, activity, student=None):
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
    student_grade_info_list = []
    if isinstance(activity, NumericActivity):
        numeric_grade_list = NumericGrade.objects.filter(activity=activity)
        for student in student_list:
            student_grade_status = None
            for numeric_grade in numeric_grade_list:
                if numeric_grade.member.person == student:
                    student_grade_status = numeric_grade.get_flag_display()
                    student_grade = str(numeric_grade.value) + '/' + str(activity.max_grade)
                    break
            if not student_grade_status:
                student_grade_status = FLAGS['NOGR']
                student_grade = '--'
            student_grade_info_list.append(StudentGradeInfo(student.id, student.name(), student.userid, student.emplid, student.email(),
                                                            student_grade_status, student_grade))
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
                student_grade = '--'
            student_grade_info_list.append(StudentGradeInfo(student.id, student.name(), student.userid, student.emplid, student.email(),
                                                            student_grade_status, student_grade))
    return student_grade_info_list
