from django.db import models
from coredata.models import Role, Person, Unit
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import coredata
import hashlib
import datetime

UPDATE_TYPES = (
    ("OPEN", "Created"),
    ("UPDT", "Automatically Updated"),
    ("EMAI", "Emailed Student"),
    ("RESO", "Manually Resolved"),
    ("COMM", "Comment"),
    ("REOP", "Re-opened")
)

class AlertType(models.Model):
    """
    An alert code.

    "GPA < 2.4"
    """
    code = models.CharField(help_text="A short (<30 characters) title for the report.", max_length=30)
    description = models.TextField(help_text="A longer, more in-depth explanation of what this alert is for.", null=True, blank=True)
    unit = models.ForeignKey(Unit, help_text="Only people in this unit can manage this Alert", null=False)
    hidden = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={})

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
    details = JSONField(null=False, blank=False, default={})
    hidden = models.BooleanField(null=False, default=False)

    # Uniqueness of an alert is complicated. In some cases, the 
    #  alert is unique to the user - for alerts on GPA < 2.4, there
    #  can only be one alert per student.
    #  In other cases, the alert
    #  is unique to the user and other fields in the output - for example
    #  an alert for students illegally retaking a course before legitimately
    #  failing it in the same semester - in this case, there can be multiple
    #  active alerts for a student.
    # 
    # Create Alerts with .safe_create, setting the unique_hash to some value
    # that must be unique to the whole Alert.
    # For GPA<2.4, this would just be emplid. For ImmediateRetake, emplid+course

    unique_hash = models.CharField(max_length=100, null=False, blank=False)
    
    resolved = models.BooleanField(null=False, default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self.alerttype.code + ": " + str(self.person)
   
    def updates(self):
        return self.alertupdate_set.filter( update_type = 'UPDT' )

    def n_updates(self):
        return self.updates().count()
    
    def emails(self):
        return self.alertupdate_set.filter( update_type = 'EMAI' )

    def n_emails(self):
        return self.emails().count()

    def comments(self):
        return self.alertupdate_set.filter( update_type = 'COMM' )

    def n_comments(self):
        return self.comments().count()

    def last_update(self):
        return self.alertupdate_set.latest('created_at')

    def last_updated(self):
        return self.last_update().created_at

    def last_resolution(self):
        return self.alertupdate_set.filter(update_type__in=["RESO", "EMAI"]).latest('created_at')

    def resolved_until(self):
        resolution = self.last_resolution()
        if resolution:
            return resolution.resolved_until
        else:
            return False

    def collision(self, collidee):
        """ 
        What to do if we try to save an object that already exists:

        Instead, create a new AlertUpdate.  
        """
        if self.resolved and self.resolved_until() and datetime.date.today() > self.resolved_until():
            update_status="REOP"
            update_comments = self.description + """
                -------
            This Alert has been re-opened. """
        else:
            update_status="UPDT"
            update_comments = self.description

        collidee.details = self.details
        collidee.save()

        update = AlertUpdate( alert=collidee, update_type=update_status, comments=update_comments ) 
        update.save()
   
    @staticmethod
    def create(dict_object, alertType, unique_fields):
        """
            Creates an Alert instance. 
            Can throw AttributeError, KeyError, SIMSProblem, IOError
        """
        if not 'EMPLID' in dict_object:
            raise AttributeError("Include an EMPLID when passing a dict to create")
        emplid = int(dict_object['EMPLID'])
        
        # this can throw a KeyError if a field is listed in unique_fields
        #   that is not also a field of dict_object
        unique_id = ":".join([dict_object[field] for field in unique_fields])

        # this can throw an IOError or SIMSProblem attempting to find the 
        #   user in SIMS, if the Person does not exist in DB
        try:
            student = Person.objects.get(emplid=emplid)
        except Person.DoesNotExist:
            student = coredata.queries.add_person( emplid )
        
        alert = Alert()
        alert.person = student
        alert.alerttype = alertType

        if 'DESCRIPTION' in dict_object:
            alert.description = dict_object['DESCRIPTION']
            del dict_object['DESCRIPTION']
        
        # The details are just 'any remaining field'
        del dict_object['EMPLID']
        alert.details = dict_object

        alert.safe_create(unique_id)
        return alert
        

    def safe_create(self, unique_id):
        """
        Save the Alert, but check to make sure that this same alert doesn't already exist, first.
        """
        # set hash
        self.unique_hash = hashlib.md5(str(unique_id)).hexdigest()
        # does this already exist? 
        objects_like_this = Alert.objects.filter( person = self.person, 
                                                  alerttype = self.alerttype, 
                                                  unique_hash = self.unique_hash ) 

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
    created_at = models.DateTimeField(auto_now_add=True)
    hidden = models.BooleanField(default=False) # not used

    # Only meaningful if update_type is "RESO"/"Resolved" 
    resolved_until = models.DateField(null=True, help_text="This will prevent this alert from being reopened until this date.")
    
    def save(self, *args, **kwargs):
        # Update the actual Alert object.
        if self.update_type in ["EMAI", "RESO"]:
            self.alert.resolved = True
            if not self.resolved_until:
                self.resolved_until = datetime.date.today()
        if self.update_type == "REOP":
            self.alert.resolved = False

        self.alert.save()

        super(AlertUpdate, self).save(*args, **kwargs)

class AlertEmailTemplate(models.Model):
    """
    An automatic e-mail to send. 
    """
    alerttype = models.ForeignKey(AlertType, null=False)
    threshold = models.IntegerField(default=0, null=False, help_text="This email will only be sent to students who have less than this many emails on file already")
    subject = models.CharField(max_length=50, null=False) 
    content = models.TextField(help_text="I.e. 'This is to confirm {{title}} {{last_name}} ... '")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Email template created by.')
    hidden = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default={})
