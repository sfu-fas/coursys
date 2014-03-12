import datetime
import fractions
from decimal import Decimal, ROUND_DOWN

from django.shortcuts import get_object_or_404

from faculty.models import CareerEvent, CareerEventManager, EVENT_TYPES, EVENT_TYPE_CHOICES, EVENT_TAGS


class FacultySummary(object):
    def __init__(self, person):
        self.person = person
   
    def salary_events(self, date):
        career_events = CareerEvent.objects.not_deleted().effective_date(date).filter(person=self.person).filter(flags=CareerEvent.flags.affects_salary).exclude(status='D')
        return career_events

    def teaching_events(self, semester):
        career_events = CareerEvent.objects.not_deleted().overlaps_semester(semester).filter(person=self.person).filter(flags=CareerEvent.flags.affects_teaching).exclude(status='D')
        return career_events
       
    def salary(self, date):
        events  = self.salary_events(date)
        tot_salary = 0
        tot_fraction = 1
        tot_bonus = 0

        for event in events:
            add_salary, salary_fraction, add_bonus = self.salary_event_info(event)
            
            tot_salary += add_salary
            tot_fraction = tot_fraction*salary_fraction
            tot_bonus += add_bonus

        pay = tot_salary * tot_fraction.numerator/tot_fraction.denominator + tot_bonus
        return Decimal(pay).quantize(Decimal('.01'), rounding=ROUND_DOWN)

    def salary_event_info(self, event):
        instance = event
        Handler = EVENT_TYPES[instance.event_type]
        handler = Handler(instance)
        add_salary, salary_fraction, add_bonus =  handler.salary_adjust_annually()

        return Decimal(add_salary).quantize(Decimal('.01'), rounding=ROUND_DOWN), salary_fraction, Decimal(add_bonus).quantize(Decimal('.01'), rounding=ROUND_DOWN)
   

    def teaching_event_info(self, event):
        instance = event
        Handler = EVENT_TYPES[instance.event_type]
        handler = Handler(instance)
        credits, load_decrease =  handler.teaching_adjust_per_semester()

        return credits, load_decrease
   

    def teaching_credits(self, semester):
        events  = self.teaching_events(semester)
        tot_credits = 0
        tot_decrease = 0

        for event in events:
            credits, load_decrease = self.teaching_event_info(event)
            
            tot_credits += credits
            tot_decrease += load_decrease

        return tot_credits, tot_decrease