from django.db import models
from coredata.models import Role, Person, Unit
from jsonfield import JSONField

ALERT_STATUSES = (
    ("OPEN", "New"),
    ("PEND", "Pending action"),
    ("RESO", "Resolved"),
    ("IGNR", "Ignored"),
    ("CONT", "Contacted"),
    ("DUPL", "Duplicate"),
)
OPEN_STATUSES = ("OPEN", "PEND")
CLOSED_STATUSES = ("RESO", "IGNR", "CONT", "DUPL")

class AlertType(models.Model):
    """
    An alert code.

    "GPA < 2.4"
    """
    code = models.CharField(help_text="The alert's code", max_length=30)
    description = models.TextField(help_text="Description of the alert.", null=True, blank=True)
    resolution_lasts = models.IntegerField(help_text="Default number of days resolution should last, defaults to 10 years.", null=False, default=3650)
    unit = models.ForeignKey(Unit, null=False)

class Alert(models.Model):
    """
    An Alert code associated with a student.
    """
    person = models.ForeignKey(Person)
    alerttype = models.ForeignKey(AlertType)
    description = models.TextField(help_text="Specific details of alert", null=True, blank=True)
    details = JSONField(null=False, blank=False, default={})  #details specific to the alert
    status = models.CharField(max_length=4, choices=ALERT_STATUSES, null=False, blank=False, default="OPEN")

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)
    #if resolved_until is nil, use the default from the 'resolution_lasts' for this alerttype
    resolved_until = models.DateField(null=True, blank=True, help_text="If resolved, til when should this resolution last?")
    
    def is_closed(self):
        return self.status in CLOSED_STATUSES
    
    def has_resolution_expired(self):
        return datetime.date.today() > self.resolved_until
    
    def default_resolved_until(self):
        period = datetime.timedelta(days=self.alerttype.resolution_lasts)
        return datetime.datetime.now() + period
    
    def save(self, *args, **kwargs):
        if self.is_closed() and not self.resolved_until:
            self.resolved_until = self.default_resolved_until()
        if self.is_closed() and not self.resolved_at:
            self.resolved_at = datetime.datetime.now()
        super(Alert, self).save(*args, **kwargs)

# Incoming Problem logic:
# 1. No matching code/student/unit: add.
# 2. Matching code/student/unit, resolved_until >= now: drop.
# 3. Matching code/student/unit, not resolved: update all fields from API (not created_at).
# 4. Matching code/student/unit, resolved_unil < now: add.


