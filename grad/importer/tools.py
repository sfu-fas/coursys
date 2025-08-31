from coredata.models import Semester
import datetime
import intervaltree


_semester_lookup = None
_strm_map = None
ONE_DAY = datetime.timedelta(days=1)


def semester_lookup(date: datetime.date) -> str:
    global _semester_lookup
    if _semester_lookup is None:
        # lazy build avoids db queries in tests before the test environment is initialized
        all_semesters = Semester.objects.all()
        interval_data = ((s.name, Semester.start_end_dates(s)) for s in all_semesters)
        intervals = (
            intervaltree.Interval(st, en+ONE_DAY, name)
            for (name, (st, en)) in interval_data)
        _semester_lookup = intervaltree.IntervalTree(intervals)
        
    return _semester_lookup[date].pop()[2]


def strm_to_semester(strm: str) -> Semester:
    global _strm_map
    if _strm_map is None:
        _strm_map = {s.name: s for s in Semester.objects.all()}
    
    return _strm_map[strm]
