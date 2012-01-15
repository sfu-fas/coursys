from django.db import models
from coredata.models import Member
from jsonfield import JSONField
from courselib.json_fields import getter_setter
import decimal

class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.ForeignKey(Member, null=False)
    base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # t.config['prep']: Preparation for labs/tutorials
        # t.config['meetings']: Attendance at planning meetings with instructor
        # t.config['lectures']: Attendance at lectures
        # t.config['tutorials']: Attendance at labs/tutorials
        # t.config['office_hours']: Office hours/student consultation
        # t.config['grading']
        # t.config['test_prep']: Quiz/exam preparation and invigilation
        # t.config['holiday']: Holiday compensation
        # Each of the above is a dictionary like:
        #     {
        #     'weekly': 2.0,
        #     'total': 26.0,
        #     'note': 'if more is required, we can revisit',
        #     }
        # t.config['other1']
        # t.config['other2']
        # As the other fields, but adding 'label'.
    
    regular_default = {'weekly': 0, 'total': 0, 'comment': ''}
    regular_fields = ['prep', 'meetings', 'lectures', 'tutorials', 'office_hours',
                  'grading', 'test_prep', 'holiday']
    other_default = {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}
    other_fields = ['other1', 'other2']
    all_fields = regular_fields + other_fields

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)



