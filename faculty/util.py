import datetime

from django.http import HttpResponse

import unicodecsv

from coredata.models import Semester


def make_csv_writer_response(filename, *args, **kwargs):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return unicodecsv.writer(response), response


class ReportingSemester(object):
    """Represents a "financial" semester

    Constructor can take one of:
        - semester code, e.g. '1141'
        - date in semester, e.g. datetime.date(2014, 1, 10)
        - Semester obj, e.g. Semester.objects.get(name='1141')

    Example:
        semester = ReportingSemester('1141')
        semester.code  -> '1141'
        semester.start_date -> Jan. 1st, 2014
        semester.end_date -> April 30th, 2014
        semester.full_label -> 'Spring 2014'
        semester.short_label -> 'sp 2014'
    """

    def __init__(self, data):
        if isinstance(data, str):
            # It's a semester code!
            self.code = data
        elif isinstance(data, datetime.date):
            # It's a date within the semester!
            self.code = self.code_from_date(data)
        elif isinstance(data, Semester):
            # It's a Semester instance!
            self.code = data.name
        else:
            raise ValueError('I was told there would be a semester code.')

        self.start_date, self.end_date = self.start_and_end_dates(self.code)
        self.full_label = self.make_full_label(self.code)
        self.short_label = self.make_short_label(self.code)

    def __hash__(self):
        return hash(self.code)

    def __cmp__(self, other):
        return cmp(self.code, other.code)

    def __repr__(self):
        return repr("<ReportingSemester('{}')>".format(self.code))

    def __unicode__(self):
        return str(self.full_label)

    def __next__(self):
        """Returns the next chronological semester."""
        new_month = ((self.start_date.month - 1) + 4) % 12 + 1

        # Did we move to the next year?
        if new_month < self.start_date.month:
            new_date = datetime.date(self.start_date.year + 1, new_month, 1)
        else:
            new_date = datetime.date(self.start_date.year, new_month, 1)

        return self.__class__(new_date)

    def prev(self):
        """Returns the previous chronological semester."""
        new_month = ((self.start_date.month - 1) - 4) % 12 + 1

        # Did we move to the previous year?
        if new_month > self.start_date.month:
            new_date = datetime.date(self.start_date.year - 1, new_month, 1)
        else:
            new_date = datetime.date(self.start_date.year, new_month, 1)

        return self.__class__(new_date)

    @classmethod
    def range(cls, start_semester_data, end_semester_data):
        """Iterates over all ReportingSemester objects within the semester code range.

        Example:
            range('1141', '1147') -> [ReportingSemester<1141>, ReportingSemester<1144>, ...]
        """
        current = cls(start_semester_data)
        end = cls(end_semester_data)

        while current <= end:
            yield current
            current = next(current)

    @staticmethod
    def make_full_label(code):
        """Makes the full label for a semester code.

        Example:
            '1141' -> 'Spring 2014'
        """
        year = int(code[:3]) + 1900
        season = code[3]
        return '{} {}'.format(Semester.label_lookup[season], year)

    @staticmethod
    def make_short_label(code):
        """Makes the short label for a semester code.

        Example:
            '1141' -> 'sp 2014'
        """
        year = int(code[:3]) + 1900
        season = code[3]
        return '{} {}'.format(Semester.slug_lookup[season], year)

    @staticmethod
    def code_from_date(date):
        """Returns the semester code that the given date falls in."""
        prefix = '{:03d}'.format(date.year - 1900)

        if date.month >= 9:
            return prefix + '7'
        elif date.month >= 5:
            return prefix + '4'
        else:
            return prefix + '1'

    @staticmethod
    def start_and_end_dates(code):
        """Returns the financial start and end dates for a semester code."""
        year = int(code[:3]) + 1900
        season = code[3]

        if season == '1':
            start = datetime.date(year, 1, 1)
            end = datetime.date(year, 4, 30)
        elif season == '4':
            start = datetime.date(year, 5, 1)
            end = datetime.date(year, 8, 31)
        elif season == '7':
            start = datetime.date(year, 9, 1)
            end = datetime.date(year, 12, 31)
        else:
            raise ValueError('Invalid semester code: {}'.format(code))

        return start, end

    @classmethod
    def current(cls):
        """Returns the current ReportingSemester."""
        return cls(datetime.date.today())
