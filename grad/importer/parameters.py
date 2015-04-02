import datetime
from coredata.models import Semester

# import grads from these units (but CMPT gets special treatment)
IMPORT_UNIT_SLUGS = ['cmpt', 'ensc', 'mse']

# in ps_acad_prog dates within about this long of the semester start are actually things that happen next semester
DATE_OFFSET = datetime.timedelta(days=30)
# ...even longer for dates of things that are startup-biased (like returning from leave)
DATE_OFFSET_START = datetime.timedelta(days=90)

SIMS_SOURCE = 'sims_source' # key in object.config to record where things came from

# don't even query data before this
IMPORT_START_SEMESTER = '1101'
IMPORT_START_DATE = Semester.start_end_dates(Semester.objects.get(name=IMPORT_START_SEMESTER))[0]

# if we find students starting before this semester, don't import
RELEVANT_PROGRAM_START = '1031'

# before this, we aren't going to worry about it.
RELEVANT_DATA_START = datetime.date(1993, 9, 1)

# be even more conservative for CMPT: this is when we started getting slightly cleaner data including adm_appl_nbr
CMPT_CUTOFF = '1137'