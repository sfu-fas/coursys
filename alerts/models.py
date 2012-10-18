from django.db import models
from coredata.models import Role, Person, Unit
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import hashlib
import datetime

UPDATE_TYPES = (
    ("OPEN", "Created"),
    ("UPDT", "Updated"),
    ("EMAI", "Emailed a Student"),
    ("CONT", "Contacted a Student"),
    ("COMM", "Comment"),
    ("RESO", "Resolved"),
    ("REOP", "Re-opened")
)

UPDATES = ["UPDT"]
ACTIONS = ["EMAI", "CONT"]
COMMENTS = ["COMM"]
RESOLUTIONS = ["RESO"]

class AlertType(models.Model):
    """
    An alert code.

    "GPA < 2.4"
    """
    code = models.CharField(help_text="The alert's code", max_length=30)
    description = models.TextField(help_text="Description of the alert.", null=True, blank=True)
    resolution_lasts = models.IntegerField(help_text="Default number of days resolution should last, defaults to 10 years.", null=False, default=3650)
    unit = models.ForeignKey(Unit, null=False)

    def autoslug(self):
        return make_slug( self.code )
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

class Alert(models.Model):
    """
    An Alert code associated with a student.
    """
    person = models.ForeignKey(Person)
    alerttype = models.ForeignKey(AlertType)
    description = models.TextField(help_text="Specific details of alert", null=True, blank=True)
    details = JSONField(null=False, blank=False, default={})  #details specific to the alert
    hidden = models.BooleanField(null=False, default=False)
    
    # generated fields
    details_hash = models.CharField(max_length=100, null=False, blank=False)
    resolved = models.BooleanField(null=False, default=False)
    updates = models.IntegerField(null=False, default=0)
    actions = models.IntegerField(null=False, default=0)
    comments = models.IntegerField(null=False, default=0)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField()
   
    def last_update(self):
        return AlertUpdate.objects.latest(created) 

    def last_resolution(self):
        return AlertUpdate.objects.filter(update_type="RESO").latest(created)

    def collision(self, collidee):
        """ 
        What to do if we try to save an object that already exists:

        Instead, create a new AlertUpdate.  
        """
        if self.resolved and datetime.datetime.now() > self.last_resolution():
            update_status="REOP"
            update_comments = self.description + """
                -------
            This Alert has been re-opened. """
        else:
            update_status="UPDT"
            update_comments = self.description

        update = AlertUpdate( alert=collidee, update_type=update_status, comments=update_comments ) 
        update.save()

    def safe_create(self):
        """
        Save the Alert, but check to make sure that this same alert doesn't already exist, first.
        """
        # set hash
        self.details_hash = hashlib.md5(str(self.details)).hexdigest()
        # does this already exist? 
        objects_like_this = Alert.objects.filter( person = self.person, 
                                                  alerttype = self.alerttype, 
                                                  details_hash = self.details_hash ) 

        if len(objects_like_this) > 0:
            self.collision( objects_like_this[0])
        else:
            self.save()
            update = AlertUpdate( alert=self, update_type="OPEN", comments=self.description ) 
            update.save()
    
    def save(self, *args, **kwargs):
        # set hash
        self.details_hash = hashlib.md5(str(self.details)).hexdigest()
        self.last_updated = datetime.datetime.now()
        super(Alert, self).save(*args, **kwargs)

class AlertUpdate(models.Model):
    """
    An update to an Alert
    """
    alert = models.ForeignKey(Alert)
    update_type = models.CharField(max_length=4, choices=UPDATE_TYPES, null=False, blank=False, default="OPEN")
    comments = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # Only meaningful if update_type is "RESO"/"Resolved" 
    resolved_until = models.DateTimeField(null=True)
    
    def save(self, *args, **kwargs):
        # Update the actual Alert object.
        if self.update_type in ACTIONS:
            self.alert.actions += 1
        if self.update_type in UPDATES:
            self.alert.updates += 1
        if self.update_type in COMMENTS:
            self.alert.comments += 1
        if self.update_type in RESOLUTIONS:
            self.alert.resolved = True
            if self.resolved_until == null:
                self.resolved_until = datetime.datetime.now() + datetime.timedelta(days=self.alert.alerttype.resolution_lasts)

        if self.update_type == "REOP":
            self.alert.resolved = False
        self.alert.last_updated = datetime.datetime.now()
        self.alert.save()

        super(AlertUpdate, self).save(*args, **kwargs)
