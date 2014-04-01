from decimal import Decimal, ROUND_DOWN

from faculty.event_types.career import SalaryBaseEventHandler
from faculty.models import CareerEvent


class FacultySummary(object):
    """Provides salary/teaching related helper methods for a Person."""

    def __init__(self, person):
        self.person = person

    def salary_events(self, date):
        """Returns all active affects_salary events that are in effect on date."""
        career_events = (CareerEvent.objects.not_deleted()
                                            .effective_date(date)
                                            .filter(person=self.person)
                                            .filter(flags=CareerEvent.flags.affects_salary)
                                            .filter(status='A'))
        return career_events

    def recent_salary(self, date):
        """Returns the most recent active affects_salary event that is in effect on date."""
        base_salary_events = self.salary_events(date).by_type(SalaryBaseEventHandler)
        return base_salary_events.order_by('-start_date').first()

    def teaching_events(self, semester):
        """Returns all active affects_teaching events that are in effect during the semester."""
        career_events = (CareerEvent.objects.not_deleted()
                                            .overlaps_semester(semester)
                                            .filter(person=self.person)
                                            .filter(flags=CareerEvent.flags.affects_teaching)
                                            .filter(status='A'))
        return career_events

    def salary(self, date):
        """Returns the person's total pay as of a given date."""
        tot_salary = 0
        tot_fraction = 1
        tot_bonus = 0

        for event in self.salary_events(date):
            add_salary, salary_fraction, add_bonus = self.salary_event_info(event)

            tot_salary += add_salary
            tot_fraction *= salary_fraction
            tot_bonus += add_bonus

        pay = tot_salary * tot_fraction.numerator/tot_fraction.denominator + tot_bonus
        return Decimal(pay).quantize(Decimal('.01'), rounding=ROUND_DOWN)

    def base_salary(self, date):
        """ Returns just the sum of the 'add_salary' info """
        salary = 0

        for event in self.salary_events(date):
            salary += self.salary_event_info(event)[0]

        return salary

    def salary_event_info(self, event):
        """Returns the rounded annual salary adjust data for an event."""
        handler = event.get_handler()
        add_salary, salary_fraction, add_bonus = handler.salary_adjust_annually()

        return (
            Decimal(add_salary).quantize(Decimal('.01'), rounding=ROUND_DOWN),
            salary_fraction,
            Decimal(add_bonus).quantize(Decimal('.01'), rounding=ROUND_DOWN),
        )

    def teaching_event_info(self, event):
        """Returns teaching adjust per semester for an event."""
        handler = event.get_handler()
        return handler.teaching_adjust_per_semester()

    def teaching_credits(self, semester):
        """Returns the person's total teaching credits and load decreases for a semester."""
        tot_credits = 0
        tot_decrease = 0

        for event in self.teaching_events(semester):
            credits, load_decrease = self.teaching_event_info(event)

            tot_credits += credits
            tot_decrease += load_decrease

        return tot_credits, tot_decrease
