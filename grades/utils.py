"""
This module collects classes and functions that are for the display purpose of Grades component
"""

from grades.models import Activity, NumericActivity, LetterActivity, NumericGrade, \
                          LetterGrade, all_activities_filter, ACTIVITY_TYPES, FLAGS, \
                          CalNumericActivity
from coredata.models import CourseOffering, Member
from grades.formulas import parse, activities_dictionary, cols_used, eval_parse, EvalException
from pyparsing import ParseException
import math
import decimal
import datetime

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}
_NO_GRADE = u'\u2014'
_DECIMAL_PLACE = 2
_SUPPORTED_GRADE_RANGE = [10]


class GradeRangeStat:
    """
    Object holding grade range stat info for the display, e.g, ('0-10', 2), ('11-20', 2), etc
    """
    def __init__(self, grade_range, stud_count):
        self.grade_range = grade_range
        self.stud_count = stud_count

class ActivityStat:
    """
    Object holding activity stat info, used as context object in template
    """
    def __init__(self, average, min, max, median, stddev, grade_range_stat_list, count):
        self.average = average
        self.min = min
        self.max = max
        self.median = median
        self.stddev = stddev
        self.grade_range_stat_list = grade_range_stat_list
        self.count = count

class ActivityStatlettergrade:
    """
    Object holding activity stat info, used as context object in template
    """
    def __init__(self,grade_range_stat_list, count):
        self.grade_range_stat_list = grade_range_stat_list
        self.count = count
        
class StudentActivityInfo:
    """
    Object holding student activity info, used as context object in template
    """
    def __init__(self, student, activity, grade_status, numeric_grade, letter_grade):
        self.student = student
        self.activity = activity
        self.grade_status = grade_status
        self.numeric_grade = numeric_grade
        self.letter_grade = letter_grade
        
    def display_grade_status_student(self):
        """
        Display student grade status from student view
        """
        if self.activity.status == 'URLS':
            return _NO_GRADE
        elif self.activity.status=="INVI":
            raise RuntimeError, "Can't display invisible grade status."
        else:
            return self.grade_status
        
    def display_grade_student(self):
        """
        Display student grade from student view
        """
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
    
    def display_grade_with_percentage_student(self):
        """
        Display student grade with percentage from student view, e.g 12/15 (80.00%)
        """
        if self.activity.status == 'URLS':
            return _NO_GRADE
        elif self.activity.status=="INVI":
            raise RuntimeError, "Can't display invisible grade."
        else:
            if self.grade_status == FLAGS['NOGR']:
                return _NO_GRADE
            else:
                if isinstance(self.activity, NumericActivity):
                    return '%s/%s (%s%%)' % (self.numeric_grade, self.activity.max_grade,
                                           format_number(float(self.numeric_grade)/float(self.activity.max_grade)*100, 2))
                elif isinstance(self.activity, LetterActivity):
                    return self.letter_grade
    
    def display_grade_staff(self):
        """
        Display student grade from staff view
        """
        if self.grade_status == FLAGS['NOGR']:
            return _NO_GRADE
        else:
            if isinstance(self.activity, NumericActivity):
                return '%s/%s' % (self.numeric_grade, self.activity.max_grade)
            elif isinstance(self.activity, LetterActivity):
                return self.letter_grade
    
    def append_activity_stat(self):
        """
        Generate activity statistics and append activity_stat attribute to the object.
        Activity statistics include: average grade, min, max, median, stddev and
        grade range statistics.
        """
        if isinstance(self.activity, NumericActivity):
            self.activity_stat = generate_numeric_activity_stat(self.activity)
        else:
            self.activity_stat = generate_letter_activity_stat(self.activity)
            
        return self
    
class FormulaTesterActivityEntry:
    def __init__(self, activity, activity_form_entry):
        self.activity = activity
        self.activity_form_entry = activity_form_entry
        

# The following fake objects are used in the formula tester
class FakeGrade(object):
     def __init__(self, value):
        self.flag = "GRAD"
        self.value = value
class FakeGradeSet(object):
     def __init__(self, grade):
        self.grade = grade
     def filter(self, **kwargs):
        return [self.grade]
class FakeActivity(object):
     def __init__(self, name, short_name, status, max_grade, percent, value):
        self.name = name
        self.short_name = short_name
        self.status = status
        self.max_grade = max_grade
        self.percent = percent
        grade = FakeGrade(value)
        self.numericgrade_set = FakeGradeSet(grade)


def reorder_course_activities(ordered_activities, activity_slug, order):
    """
    Reorder the activity in the Activity list of a course according to the
    specified order action. Please make sure the Activity list belongs to
    the same course.
    """
    for activity in ordered_activities:
        if not isinstance(activity, Activity):
            raise TypeError(u'ordered_activities should be list of Activity')
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
    Return a list of StudentActivityInfo object which contains all enrolled
    students' activity info in a course. If student param is specified,
    the list will contain only one StudentActivityInfo object for that
    student.
    """
    if not course or not activity:
        return
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        raise TypeError(u'Activity type is required')
    if not isinstance(course, CourseOffering):
        raise TypeError(u'CourseOffering type is required')
    # verify if the course contains the activity
    if not Activity.objects.filter(slug=activity.slug, offering=course):
        return
    student_list = Member.objects.filter(offering=course, role='STUD')
    if student:
        if not isinstance(student, Member):
            raise TypeError(u'Member type is required')
        if student in student_list:
            student_list = [student]
        else:
            return
    
    student_activity_info_list = []
    
    if isinstance(activity, NumericActivity):
        # select_ralated field for fast template rendering
        #numeric_grade_list = NumericGrade.objects.filter(activity=activity).select_related('member', 'member__person')
        numeric_grade_list = activity.numericgrade_set.all().select_related('member', 'member__person', 'activity')
        for student in student_list:
            student_grade_status = None
            for numeric_grade in numeric_grade_list:
                if numeric_grade.member == student:
                    student_grade_status = numeric_grade.get_flag_display()
                    student_grade = numeric_grade.value
                    break
            if not student_grade_status:
                student_grade_status = FLAGS['NOGR']
                student_grade = None
            student_activity_info_list.append(StudentActivityInfo(student, activity,
                                                                  student_grade_status, student_grade, None))
    elif isinstance(activity, LetterActivity):
        # select_ralated field for fast template rendering
        letter_grade_list = LetterGrade.objects.filter(activity=activity).select_related('member', 'member__person')
        for student in student_list:
            student_grade_status = None
            for letter_grade in letter_grade_list:
                if letter_grade.member == student:
                    student_grade_status = letter_grade.get_flag_display()
                    student_grade = letter_grade.letter_grade
                    break
            if not student_grade_status:
                student_grade_status = FLAGS['NOGR']
                student_grade = None
            student_activity_info_list.append(StudentActivityInfo(student, activity,
                                                                  student_grade_status, None, student_grade))
    return student_activity_info_list

def generate_numeric_activity_stat(activity):
    """
    This function fetch statistics of the numeric activity.
    """
    student_grade_list = fetch_students_numeric_grade(activity)
    if not student_grade_list:
        return
    student_grade_list.sort()
    student_grade_list_count = len(student_grade_list)
    average = sum(student_grade_list)
    average = float(average) / student_grade_list_count
    
    if student_grade_list_count % 2 == 0:
        median = (student_grade_list[(student_grade_list_count - 1) / 2] +
                    student_grade_list[(student_grade_list_count) / 2]) / 2
    else:
        median = student_grade_list[(student_grade_list_count - 1) / 2]

    stddev = math.sqrt(sum([(float(student_grade) - average) ** 2 for student_grade in student_grade_list]) / student_grade_list_count)
    
    # normalize the grade into 100 based in order to generate the grade range stat
    if activity.max_grade == 0:
        normalized_student_grade_list = [100 for student_grade in student_grade_list]
    else:
        normalized_student_grade_list = [ float(student_grade)/float(activity.max_grade)*100
                                        for student_grade in student_grade_list ]
    grade_range_stat_list = generate_grade_range_stat(normalized_student_grade_list)

    return ActivityStat(format_number(average, _DECIMAL_PLACE), format_number(student_grade_list[0], _DECIMAL_PLACE),
                        format_number(student_grade_list[student_grade_list_count - 1], _DECIMAL_PLACE),
                        format_number(median, _DECIMAL_PLACE),
                        format_number(stddev, _DECIMAL_PLACE), grade_range_stat_list, student_grade_list_count)
##########################################################################################################################
def generate_letter_activity_stat(activity):
    """
    This function fetch statistics of the numeric activity.
    """
    student_grade_list = fetch_students_letter_grade(activity)
    if not student_grade_list:
        return

    student_grade_list_count = len(student_grade_list)
    grade_range_stat_list = generate_grade_range_stat_lettergrade(student_grade_list)

    return ActivityStatlettergrade(grade_range_stat_list, student_grade_list_count)
    

   
    
############################################################################################################################    
def generate_grade_range_stat(student_grade_list, grade_range=10):
    """
    This function return a order list of GradeRangeStat according to the grade_range param.
    Grade range equal to 10 means divide max grade into intervals with 10 grades each. The
    max grade is default to 100. Thus the grade in the student_grade_list param should be
    normalized to 100 based. E.g. the function will gerenate a grade range list:
    ('0-10', 1), ('11-20', 2), ('21-30', 0), ('31-40', 1), ('41-50', 5),
    ('51-60', 10), ('61-70', 12), ('71-80', 7), ('81-90', 3), ('91-100', 1)
    """
    """
    The ranges except the last one are half-open ranges. Say:
    [0,10), [10,20), [20,30), [30,40), [40,50), [50,60), [60,70), [70,80), [80,90), [90,100]
    """
    if not grade_range in _SUPPORTED_GRADE_RANGE:
        return
    EPS = 1e-6
    if grade_range == 10:
        lower = float(min(student_grade_list))/10.0
        upper = float(max(student_grade_list))/10.0
        if lower < int(lower) - EPS:
            lower -= 1
        lower = int(min(lower, 0))
        if upper > int(upper) + EPS:
            upper += 1
        upper = int(max(upper, grade_range))

        grade_range_stat_list = []
        for i in range(lower, upper):
            stud_count = len([k for k in student_grade_list if k >= i*10 and k < (i+1)*10])
            grade_range_stat_list.append(GradeRangeStat('%d-%d' % (i * 10, (i + 1) * 10), stud_count))
        grade_range_stat_list[-1].stud_count += len([k for k in student_grade_list if k >= (i+1)*10])
        return grade_range_stat_list

#    if grade_range == 10:
#        grade_range_stat_list = [GradeRangeStat('0-10', 0), GradeRangeStat('11-20', 0), GradeRangeStat('21-30', 0),
#                             GradeRangeStat('31-40', 0), GradeRangeStat('41-50', 0), GradeRangeStat('51-60', 0),
#                             GradeRangeStat('61-70', 0), GradeRangeStat('71-80', 0), GradeRangeStat('81-90', 0),
#                             GradeRangeStat('91-100', 0)]
#        for student_grade in student_grade_list:
#            if student_grade <= 10:
#                grade_range_stat_list[0].stud_count += 1
#            elif 11 <= student_grade and student_grade <=20:
#                grade_range_stat_list[1].stud_count += 1
#            elif 21 <= student_grade and student_grade <=30:
#                grade_range_stat_list[2].stud_count += 1
#            elif 31 <= student_grade and student_grade <=40:
#                grade_range_stat_list[3].stud_count += 1
#            elif 41 <= student_grade and student_grade <=50:
#                grade_range_stat_list[4].stud_count += 1
#            elif 51 <= student_grade and student_grade <=60:
#                grade_range_stat_list[5].stud_count += 1
#            elif 61 <= student_grade and student_grade <=70:
#                grade_range_stat_list[6].stud_count += 1
#            elif 71 <= student_grade and student_grade <=80:
#                grade_range_stat_list[7].stud_count += 1
#            elif 81 <= student_grade and student_grade <=90:
#                grade_range_stat_list[8].stud_count += 1
#            elif 91 <= student_grade:
#                grade_range_stat_list[9].stud_count += 1
#        return grade_range_stat_list
    
def generate_grade_range_stat_lettergrade(student_lettergrade_list,grade_range=11):
	if grade_range ==11:
            grade_range_stat_list = [GradeRangeStat('F', 0), GradeRangeStat('D', 0), GradeRangeStat('C-', 0),
                             GradeRangeStat('C', 0), GradeRangeStat('C+', 0), GradeRangeStat('B-', 0),
                             GradeRangeStat('B', 0), GradeRangeStat('B+', 0), GradeRangeStat('A-', 0),
                             GradeRangeStat('A', 0),GradeRangeStat('A+', 0)]

        for student_grade in student_lettergrade_list:
            if student_grade == 'A+':
                grade_range_stat_list[10].stud_count += 1
            elif student_grade == 'A':
                grade_range_stat_list[9].stud_count += 1
            elif student_grade == 'A-':
                grade_range_stat_list[8].stud_count += 1
            elif student_grade == 'B+':
                grade_range_stat_list[7].stud_count += 1
            elif student_grade == 'B':
                grade_range_stat_list[6].stud_count += 1
            elif student_grade == 'B-':
                grade_range_stat_list[5].stud_count += 1
            elif student_grade == 'C+':
                grade_range_stat_list[4].stud_count += 1
            elif student_grade == 'C':
                grade_range_stat_list[3].stud_count += 1
            elif student_grade == 'C-':
                grade_range_stat_list[2].stud_count += 1
            elif student_grade == 'D':
                grade_range_stat_list[1].stud_count += 1
            elif student_grade == 'F':
                grade_range_stat_list[0].stud_count += 1
            elif student_grade == 'A':
                grade_range_stat_list[9].stud_count += 1
            elif student_grade == 'A-':
                grade_range_stat_list[8].stud_count += 1
            elif student_grade == 'B+':
                grade_range_stat_list[7].stud_count += 1
            elif student_grade == 'B':
                grade_range_stat_list[6].stud_count += 1
            elif student_grade == 'B-':
                grade_range_stat_list[5].stud_count += 1
            elif student_grade == 'C+':
                grade_range_stat_list[4].stud_count += 1
            elif student_grade == 'C':
                grade_range_stat_list[3].stud_count += 1
            elif student_grade == 'C-':
                grade_range_stat_list[2].stud_count += 1
            elif student_grade == 'D':
                grade_range_stat_list[1].stud_count += 1
            elif student_grade == 'F':
                grade_range_stat_list[0].stud_count += 1
        return grade_range_stat_list

def fetch_students_numeric_grade(activity):
    """
    This function return a list of all students' grade in a course activity. If student does not
    have any grade yet, the numeric grade is default to 0.
    """
    _DEFAULT_NUMERIC_GRADE = 0

    student_list = activity.offering.members.filter(person__role='STUD')
    grade_list = NumericGrade.objects.filter(activity=activity).exclude(flag="NOGR")\
                        .select_related('member','member__person') 
    
    student_grade_list = []
    for student in student_list:
        student_found = False
        for grade in grade_list:
            if grade.member.person == student:
                student_found = True
                student_grade_list.append(grade.value)
                break
        #if not student_found:
        #    student_grade_list.append(_DEFAULT_NUMERIC_GRADE)
    
    return student_grade_list

def fetch_students_letter_grade(activity):
    """
    This function return a list of all students' grade in a course activity. If student does not
    have any grade yet, the numeric grade is default to 0.
    """


    student_list = activity.offering.members.filter(person__role='STUD')
    grade_list = LetterGrade.objects.filter(activity=activity).exclude(flag="NOGR")\
                        .select_related('member','member__person') 
    
    student_grade_list = []
    for student in student_list:
        student_found = False
        for grade in grade_list:
            if grade.member.person == student:
                student_found = True
                student_grade_list.append(grade.letter_grade)
                break
        #if not student_found:
        #    student_grade_list.append(_DEFAULT_NUMERIC_GRADE)
    
    return student_grade_list

######################################################################################################t

###############################################################################################################   
def format_number(value, decimal_places):
    """
    Formats a number into a string with the requisite number of decimal places.
    """
    if isinstance(value, decimal.Decimal):
        context = decimal.getcontext().copy()
        return u'%s' % str(value.quantize(decimal.Decimal(".1") ** decimal_places, context=context))
    else:
        return u"%.*f" % (decimal_places, value)



class ValidationError(Exception):
    pass

def parse_and_validate_formula(formula, numeric_activities):
    """
    Handy function to parse the formula and validate if the activity references
    in the formula are in the numeric_activities list
    Return the parsed formula if no exception raised
    
    May raise exception: ParseException, ValidateError
    """
    for activity in numeric_activities:
        if not isinstance(activity, NumericActivity):
            raise TypeError(u'NumericActivity list is required')
    try:
        parsed_expr = parse(formula)
        activities_dict = activities_dictionary(numeric_activities)
        cols = set([])
        cols = cols_used(parsed_expr)
        for col in cols:
            if not col in activities_dict:
                raise ValidationError(u'Invalid activity reference')
    except ParseException:
        raise ValidationError(u'Incorrect formula syntax')
    return parsed_expr

def calculate_numeric_grade(course, activity, student=None):
    """
    Calculate all the student's grade in the course's CalNumericActivity.
    If student param is specified, this student's grade is calculated instead
    of the whole class, please also make sure this student is in the course
    before passing the student param.
    """
    if not isinstance(course, CourseOffering):
        raise TypeError('CourseOffering type is required')
    if not isinstance(activity, CalNumericActivity):
        raise TypeError('CalNumericActivity type is required')

    numeric_activities = NumericActivity.objects.filter(offering=course, deleted=False)
    act_dict = activities_dictionary(numeric_activities)
    try:
        parsed_expr = parse_and_validate_formula(activity.formula, numeric_activities)
    except ValidationError as e:
        raise ValidationError('Formula Error: ' + e.args[0])
        
    if student != None: # calculate for one student
        if not isinstance(student, Member):
            raise TypeError('Member type is required')
        student_list = [student]
        try:
            numeric_grade = NumericGrade.objects.get(activity = activity, member=student)
        except NumericGrade.DoesNotExist:
            numeric_grade_list = []
        else:
            numeric_grade_list = [numeric_grade]
    else: # calculate for all student
        student_list = Member.objects.filter(offering=course, role='STUD')
        numeric_grade_list = NumericGrade.objects.filter(activity = activity).select_related('member')
    
    ignored = 0
    for s in student_list:
        # calculate grade
        try:
            result = eval_parse(parsed_expr, act_dict, s, activity.status=="RLS")
            result = decimal.Decimal(str(result)) # convert to decimal
        except EvalException:
            raise EvalException("Formula Error: Can not evaluate formula for student: '%s'" % s.person.name())
        
        # save grade
        member_found = False
        for numeric_grade in numeric_grade_list:
            if numeric_grade.member == s:
                member_found = True     
                if numeric_grade.flag == "GRAD":
                    ignored += 1
                elif result != numeric_grade.value:
                    # ignore manually-set grades; only save when the value changes
                    numeric_grade.value = result
                    numeric_grade.save(newsitem=False)
                break
        if not member_found:
            numeric_grade = NumericGrade(activity=activity, member=s,
                                         value=str(result), flag='CALC')
            numeric_grade.save(newsitem=False)
    if student != None:
        return StudentActivityInfo(student, activity, FLAGS['CALC'], numeric_grade.value, None).display_grade_staff()
    else:
        return ignored
