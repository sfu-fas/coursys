import datetime

class Semester(int):
    
    SPRING = 1
    SUMMER = 4
    FALL = 7
    
    def year(self):
        """Return the calendar year.

        >>> Semester(934).year()
        1993
        >>> Semester(1021).year()
        2002
        """

        return 1900 + self/10
    
    def code(self):
        """ Return the semester code

        (1 for Spring, 4 for Summer, 7 for Fall).

        >>> Semester(934).code()
        4
        >>> Semester(1021).code()
        1
        """
        return int(self) % 10

    def increment(self, count=1):
        """ Add one semester to the current semester
        
            - or, change the semester by 'count' in any direction.
        """
        temp_year = self.year()
        temp_code = self.code() + 3 * (count % 3)     
        if temp_code >= 10:
            temp_code -= 9
            temp_year += 1
        temp_year += count/3
        return Semester((temp_year - 1900) * 10 + temp_code)

    def start_date(self):
        """The first day of the semester (first day of month) as a date object.

        Note that semester start date may also be retrieved from
        PS_TERM_TBL as TERM_START_DATE, using ACAD_CAREER='CNED'.
        
        >>> Semester('1114').start_date()
        datetime.date(2011, 5, 1)
        >>> Semester('837').start_date()
        datetime.date(1983, 9, 1)
        """
        year = self.year()
        code = self.code()
        if code == self.SPRING: month = 1
        elif code == self.SUMMER: month = 5
        elif code == self.FALL: month = 9
        elif code == 0: month = 1
        return datetime.date(year, month, 1)
    
    def mid_date(self):
        """The first day of the middle of the semester (first day of month) as a date object.
        
        >>> Semester('1114').mid_date()
        datetime.date(2011, 7, 1)
        >>> Semester('837').mid_date()
        datetime.date(1983, 11, 1)
        """
        year = self.year()
        code = self.code()
        if code == self.SPRING: month = 3
        elif code == self.SUMMER: month = 7
        elif code == self.FALL: month = 11
        elif code == 0: month = 1
        return datetime.date(year, month, 1)

    def long_form(self):
        """ Returns the semester as a real semester, a-la "Fall 2007"

        >>> Semester('1114').long_form()
        'Summer 2011'
        >>> Semester('837').long_form()
        'Fall 1983'
        """
        sem_string = ""
        year = self.year()
        code = self.code()
        if code == self.SPRING: sem_string += "Spring "
        elif code == self.SUMMER: sem_string += "Summer "
        elif code == self.FALL: sem_string += "Fall "
        sem_string += str(year)

        return sem_string 

def date2semester(toconvert):
    """Given a date as a datetime object, return the Semester
    in which the date is contained.

    >>> date2semester(datetime.date(1977,3,22))
    771

    """
    semcode = 1+(3*((toconvert.month-1)/4))
    return Semester( (toconvert.year - 1900) * 10 + semcode )

def current_semester():
    """Return the current semester as of the date today().
    """
    return date2semester(datetime.date.today())

def previous_semester():
    """Return the semester preceding this one.
    """
    return current_semester().increment(-1)

def semester_range( start_semester, end_semester):
    """ Return a range of semesters, from start_semester 
        to end_semester
    """
    current_semester = start_semester
    while current_semester != end_semester:
        yield current_semester
        current_semester = current_semester.increment() 
    yield current_semester

__Today = datetime.date.today()
def registration_semester(as_of_date = __Today):
    """Return the next registration semester that applies
    for a given date according to the following rule: the
    registration semester is the current semester during the
    first month of the semester, otherwise it is the next semester.

    If no argument is specified, the registration semester as of
    the date today() is specified.

    >>> registration_semester(Semester(1047).mid_date())
    1051
    """
    this_semester = date2semester(as_of_date)
    if (as_of_date.month - 1) % 4 == 0: return this_semester
    else: return this_semester.increment()
    
def fall_admission_semester(as_of_date = __Today):
    """Return the next fall admission semester that applies
    for a given date according to the following rule: the
    fall admission semester is the fall semester of the
    current year upto until the end of September, after
    which it is the fall semester of the next year.

    >>> fall_admission_semester(Semester(1037).start_date())
    1037
    >>> fall_admission_semester(Semester(1037).mid_date())
    1047
    >>> fall_admission_semester(Semester(991).start_date())
    997
    """
    year_code_base = (as_of_date.year - 1900) * 10
    if as_of_date.month <= 9:
        return year_code_base + Semester.FALL
    else:
        return year_code_base + 10 + Semester.FALL

