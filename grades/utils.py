"""
This module collects classes and functions that are for the display purpose of Grades component
"""

from grades.models import Activity, NumericActivity, LetterActivity, NumericGrade, \
                          LetterGrade, ACTIVITY_TYPES, FLAGS, \
                          CalNumericActivity,CalLetterActivity, median_letters, min_letters, max_letters,sorted_letters
from coredata.models import CourseOffering, Member
from grades.formulas import parse, activities_dictionary, cols_used, eval_parse, EvalException
from pyparsing import ParseException
import math
import decimal

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}
_NO_GRADE = '\u2014'
_DECIMAL_PLACE = 2
_SUPPORTED_GRADE_RANGE = [10]

# Course should have this number to student to display the activity statistics, including histogram
STUD_NUM_TO_DISP_ACTSTAT = 10

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
    def __init__(self,grade_range_stat_list, count, median, min, max):
        self.grade_range_stat_list = grade_range_stat_list
        self.count = count
        self.median = median
        self.min = min
        self.max = max

        
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
            raise RuntimeError("Can't display invisible grade status.")
        else:
            return self.grade_status
        
    def display_grade_student(self):
        """
        Display student grade from student view
        """
        if self.activity.status == 'URLS':
            return _NO_GRADE
        elif self.activity.status=="INVI":
            raise RuntimeError("Can't display invisible grade.")
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
            raise RuntimeError("Can't display invisible grade.")
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
class FakeEvalActivity(object):
    def __init__(self, course):
        self.id = -1
        self.offering = course
    def calculation_leak(self):
        return False


def reorder_course_activities(ordered_activities, activity_slug, order):
    """
    Reorder the activity in the Activity list of a course according to the
    specified order action. Please make sure the Activity list belongs to
    the same course.
    """
    for activity in ordered_activities:
        if not isinstance(activity, Activity):
            raise TypeError('ordered_activities should be list of Activity')
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
        raise TypeError('Activity type is required')
    if not isinstance(course, CourseOffering):
        raise TypeError('CourseOffering type is required')
    # verify if the course contains the activity
    if not Activity.objects.filter(slug=activity.slug, offering=course):
        return
    student_list = Member.objects.filter(offering=course, role='STUD')
    if student:
        if not isinstance(student, Member):
            raise TypeError('Member type is required')
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

def generate_numeric_activity_stat(activity, role):
    """
    This function fetch statistics of the numeric activity.
    """
    if role == 'STUD' and activity.status != 'RLS':
        return None, 'Summary statistics disabled for unreleased activities.'

    student_grade_list = fetch_students_numeric_grade(activity)
    if not student_grade_list:
        if role == 'STUD':
            return None, 'Summary statistics disabled for small classes.'
        else:
            return None, 'No grades assigned.'
    if role == 'STUD' and not activity.showstats():
        return None, 'Summary stats disabled by instructor.'

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
    if role == 'STUD' and not activity.showhisto():
        grade_range_stat_list = []
    else:
        grade_range_stat_list = generate_grade_range_stat(normalized_student_grade_list)

    stats = ActivityStat(format_number(average, _DECIMAL_PLACE), format_number(student_grade_list[0], _DECIMAL_PLACE),
                        format_number(student_grade_list[student_grade_list_count - 1], _DECIMAL_PLACE),
                        format_number(median, _DECIMAL_PLACE),
                        format_number(stddev, _DECIMAL_PLACE), grade_range_stat_list, student_grade_list_count)

    reason_msg = ''
    if role == 'STUD' and (stats is None or stats.count < STUD_NUM_TO_DISP_ACTSTAT):
        reason_msg = 'Summary statistics disabled for small classes.'
        stats = None

    return stats, reason_msg

##########################################################################################################################
def generate_letter_activity_stat(activity, role):
    """
    This function fetch statistics of the numeric activity.
    """
    if role == 'STUD' and activity.status != 'RLS':
        return None, 'Summary statistics disabled for unreleased activities.'

    student_grade_list = fetch_students_letter_grade(activity)
    sorted_grades = sorted_letters(student_grade_list) 
    if not sorted_grades:
        if role == 'STUD':
            return None, 'Summary statistics disabled for small classes.'
        else:
            return None, 'No grades assigned.'
    if role == 'STUD' and not activity.showstats():
        return None, 'Summary stats disabled by instructor.'

    student_grade_list_count = len(student_grade_list)
    if role == 'STUD' and not activity.showhisto():
        grade_range_stat_list = []
    else:
        grade_range_stat_list = generate_grade_range_stat_lettergrade(student_grade_list)
    median=median_letters(sorted_grades)
    max=max_letters(sorted_grades)
    min=min_letters(sorted_grades)

    stats = ActivityStatlettergrade(grade_range_stat_list, student_grade_list_count,median,min,max)

    reason_msg = ''
    if role == 'STUD' and (stats is None or stats.count < STUD_NUM_TO_DISP_ACTSTAT):
        reason_msg = 'Summary statistics disabled for small classes.'
        stats = None

    return stats, reason_msg


   
    
############################################################################################################################    
def generate_grade_range_stat(student_grade_list, grade_range=10):
    """
    This function return a order list of GradeRangeStat according to the grade_range param.
    Grade range equal to 10 means divide max grade into intervals with 10 grades each. The
    max grade is default to 100. Thus the grade in the student_grade_list param should be
    normalized to 100 based. E.g. the function will gerenate a grade range list:
    ('0-10', 1), ('11-20', 2), ('21-30', 0), ('31-40', 1), ('41-50', 5),
    ('51-60', 10), ('61-70', 12), ('71-80', 7), ('81-90', 3), ('91-100', 1)

    The ranges except the last one are half-open ranges. Say:
    [0,10), [10,20), [20,30), [30,40), [40,50), [50,60), [60,70), [70,80), [80,90), [90,100]
    """
    if not grade_range in _SUPPORTED_GRADE_RANGE:
        return
    EPS = 1e-6
    
    stats = [GradeRangeStat("<0%", 0)] \
            + [GradeRangeStat("%i\u2013%i%%" % (i*grade_range,(i+1)*grade_range), 0) for i in range(grade_range)] \
            + [GradeRangeStat(">100%", 0)]
    for g in student_grade_list:
        # extreme cases:
        if g < 0:
            stats[0].stud_count += 1
        elif g > 100:
            stats[-1].stud_count += 1
        else:
            # other grade_range bins:
            bin = int(g//10 + EPS)
            if bin == grade_range:
                # move 100% down into x-100 bin
                bin -= 1
            stats[bin+1].stud_count += 1
    
    # remove extreme bins if not used
    if stats[0].stud_count == 0:
        stats = stats[1:]
    if stats[-1].stud_count == 0:
        stats = stats[:-1]
    
    return stats

    
def generate_grade_range_stat_lettergrade(student_lettergrade_list,grade_range=11):
	if grade_range ==11:
            grade_range_stat_list = [GradeRangeStat('other', 0), GradeRangeStat('F', 0), GradeRangeStat('D', 0), GradeRangeStat('C-', 0),
                             GradeRangeStat('C', 0), GradeRangeStat('C+', 0), GradeRangeStat('B-', 0),
                             GradeRangeStat('B', 0), GradeRangeStat('B+', 0), GradeRangeStat('A-', 0),
                             GradeRangeStat('A', 0),GradeRangeStat('A+', 0)]

        for student_grade in student_lettergrade_list:
            if student_grade == 'A+':
                grade_range_stat_list[11].stud_count += 1
            elif student_grade == 'A':
                grade_range_stat_list[10].stud_count += 1
            elif student_grade == 'A-':
                grade_range_stat_list[9].stud_count += 1
            elif student_grade == 'B+':
                grade_range_stat_list[8].stud_count += 1
            elif student_grade == 'B':
                grade_range_stat_list[7].stud_count += 1
            elif student_grade == 'B-':
                grade_range_stat_list[6].stud_count += 1
            elif student_grade == 'C+':
                grade_range_stat_list[5].stud_count += 1
            elif student_grade == 'C':
                grade_range_stat_list[4].stud_count += 1
            elif student_grade == 'C-':
                grade_range_stat_list[3].stud_count += 1
            elif student_grade == 'D':
                grade_range_stat_list[2].stud_count += 1
            elif student_grade == 'F':
                grade_range_stat_list[1].stud_count += 1
            else:
                grade_range_stat_list[0].stud_count += 1

        if grade_range_stat_list[0].stud_count == 0:
            # no "other": don't display
            grade_range_stat_list = grade_range_stat_list[1:]

        return grade_range_stat_list

def fetch_students_numeric_grade(activity):
    """
    This function return a list of all students' grade in a course activity.
    """
    student_list = activity.offering.members.filter(person__role='STUD')
    grade_list = NumericGrade.objects.filter(activity=activity).exclude(flag="NOGR")\
                        .select_related('member','member__person') 
    
    student_grade_list = []
    for student in student_list:
        #student_found = False
        for grade in grade_list:
            if grade.member.person == student:
                #student_found = True
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
        #student_found = False
        for grade in grade_list:
            if grade.member.person == student:
                #student_found = True
                student_grade_list.append(grade.letter_grade)
                break
        #if not student_found:
        #    student_grade_list.append(_DEFAULT_NUMERIC_GRADE)
    
    return student_grade_list

def calculate_letter_grade(course, activity):
    """
    Calculate all the student's grade in the course's CalletterActivity.
    If student param is specified, this student's grade is calculated instead
    of the whole class, please also make sure this student is in the course
    before passing the student param.
    """
    if not isinstance(course, CourseOffering):
        raise TypeError('CourseOffering type is required')
    if not isinstance(activity, CalLetterActivity):
        raise TypeError('CalLetterActivity type is required')

    # calculate for all student
    student_list = Member.objects.filter(offering=course, role='STUD')
    letter_grade_list = LetterGrade.objects.filter(activity = activity).select_related('member') 
   
    ignored = 0
    for s in student_list:
        # calculate grade

        result = generate_lettergrades(s,activity)

        # save grade
        member_found = False
        for letter_grade in letter_grade_list:
            if letter_grade.member == s:
                member_found = True     
                if letter_grade.flag != "CALC":
                    ignored += 1
                elif result != letter_grade.letter_grade or letter_grade.flag != "CALC":
                    # ignore manually-set grades; only save when the value changes
                    letter_grade.letter_grade = result
                    letter_grade.flag = "CALC"
                    letter_grade.save(newsitem=False, entered_by=None)
                break
        if not member_found:
            letter_grade = LetterGrade(activity=activity, member=s,
                                         letter_grade=result, flag='CALC')
            letter_grade.save(newsitem=False, entered_by=None)
    return ignored

def generate_lettergrades(s,activity):
    
    cutoffs=activity.get_cutoffs()
    numeric_source = activity.numeric_activity
    exam_activity=activity.exam_activity
    
    if exam_activity:
        # handle the N and DE logic from the exam activity
        exam_grades = NumericGrade.objects.filter(activity=exam_activity, member=s) or LetterGrade.objects.filter(activity=exam_activity, member=s)
        if len(exam_grades)==0 or exam_grades[0].flag == 'NOGR':
            return 'N'
        elif exam_grades[0].flag == 'EXCU':
            return 'DE'

    grades = NumericGrade.objects.filter(activity=numeric_source, member=s)
    if len(grades)==0 or grades[0].flag=='NOGR':
        return 'N'

    grade = grades[0].value

    if grade>=cutoffs[0]:
        letter_grade='A+'
    elif grade>=cutoffs[1]:
        letter_grade='A'
    elif grade>=cutoffs[2]:
        letter_grade='A-'
    elif grade>=cutoffs[3]:
        letter_grade='B+'
    elif grade>=cutoffs[4]:
        letter_grade='B'
    elif grade>=cutoffs[5]:
        letter_grade='B-'
    elif grade>=cutoffs[6]:
        letter_grade='C+'
    elif grade>=cutoffs[7]:
        letter_grade='C'
    elif grade>=cutoffs[8]:
        letter_grade='C-'
    elif grade>=cutoffs[9]:
        letter_grade='D'
    else:
        letter_grade='F'
    
    return letter_grade

###############################################################################################################   
def format_number(value, decimal_places):
    """
    Formats a number into a string with the requisite number of decimal places.
    """
    if isinstance(value, decimal.Decimal):
        context = decimal.getcontext().copy()
        return '%s' % str(value.quantize(decimal.Decimal(".1") ** decimal_places, context=context))
    else:
        return "%.*f" % (decimal_places, value)



class ValidationError(Exception):
    pass

def parse_and_validate_formula(formula, course, activity, numeric_activities):
    """
    Handy function to parse the formula and validate if the activity references
    in the formula are in the numeric_activities list
    Return the parsed formula if no exception raised
    
    May raise exception: ParseException, ValidateError
    """
    for a in numeric_activities:
        if not isinstance(a, NumericActivity):
            raise TypeError('NumericActivity list is required')
    try:
        parsed_expr = parse(formula, course, activity)
        activities_dict = activities_dictionary(numeric_activities)
        cols = set([])
        cols = cols_used(parsed_expr)
        for col in cols:
            if not col in activities_dict:
                raise ValidationError('Invalid activity reference')
    except ParseException:
        raise ValidationError('Incorrect formula syntax')
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
        parsed_expr = parse_and_validate_formula(activity.formula, activity.offering, activity, numeric_activities)
    except ValidationError as e:
        raise ValidationError('Formula Error: ' + e.args[0])
        
    if student != None: # calculate for one student
        if not isinstance(student, Member):
            raise TypeError('Member type is required')
        student_list = [student]
        numeric_grade_list = NumericGrade.objects.filter(activity=activity, member=student)
    else: # calculate for all student
        student_list = Member.objects.filter(offering=course, role='STUD')
        numeric_grade_list = NumericGrade.objects.filter(activity = activity).select_related('member')
    
    ignored = 0
    visible = activity.status=="RLS"
    for s in student_list:
        # calculate grade
        try:
            result = eval_parse(parsed_expr, activity, act_dict, s, visible)
            result = decimal.Decimal(str(result)) # convert to decimal
        except EvalException:
            raise EvalException("Formula Error: Can not evaluate formula for student: '%s'" % s.person.name())
        
        # save grade
        member_found = False
        for numeric_grade in numeric_grade_list:
            if numeric_grade.member == s:
                member_found = True     
                if numeric_grade.flag != "CALC":
                    # ignore manually-set grades
                    ignored += 1
                elif result != numeric_grade.value:
                    # only save when the value changes
                    numeric_grade.value = result
                    numeric_grade.flag = "CALC"
                    numeric_grade.save(newsitem=False, entered_by=None)
                break
        if not member_found:
            numeric_grade = NumericGrade(activity=activity, member=s,
                                         value=str(result), flag='CALC')
            numeric_grade.save(newsitem=False, entered_by=None)

    uses_unreleased = True in (act_dict[c].status != 'RLS' for c in cols_used(parsed_expr))
    hiding_info = visible and uses_unreleased and not activity.calculation_leak()

    if student != None:
        return StudentActivityInfo(student, activity, FLAGS['CALC'], numeric_grade.value, None).display_grade_staff(), hiding_info
    else:
        return ignored, hiding_info
