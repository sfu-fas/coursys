import abc


class CareerEventMixinBase(object, metaclass=abc.ABCMeta):

    FLAGS = []


class TeachingCareerEvent(CareerEventMixinBase):
    '''
    Equivalent to the 'affects_teaching' flag.
    '''

    FLAGS = ['affects_teaching']

    @abc.abstractmethod
    def teaching_adjust_per_semester(self):
        """
        Return vector of ways this CareerEvent affects the faculty member's
        teaching expectation. Must be a namedtuple:
            TeachingAdjust(credits, load_decrease).
        Each value is interpreted as "courses PER SEMESTER".
            courses_taught += credits * n_semesters
            teaching_owed -= load_decrease * n_semesters

        e.g.
            return TeachingAdjust(Fraction(1,2), Fraction(1,2))
            return TeachingAdjust(Fraction(0), Fraction(1))
        These might indicate respectively an admin position with a 1.5 course/year
        teaching credit, and a medical leave with a 3 course/year reduction in
        workload.

        """
        pass


class SalaryCareerEvent(CareerEventMixinBase):
    '''
    Equivalent to the 'affects_salary' flag.
    '''

    FLAGS = ['affects_salary']

    # Override these

    @abc.abstractmethod
    def salary_adjust_annually(self):
        '''
        Return vector of ways this CareerEvent affects the faculty member's
        salary. Must be a namedtuple: SalaryAdjust(add_salary, salary_fraction, add_bonus).
        So, pay after is event is:
            pay = (pay + add_salary) * salary_fraction + add_bonus
        e.g.
            return SalaryAdjust(Decimal('5000.01'), Fraction(4,5), Decimal(10000))

        '''
        pass
