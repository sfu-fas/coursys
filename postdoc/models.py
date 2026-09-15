from django.db import models
from django.urls import reverse
import os
from coredata.models import Person, Unit
from courselib.json_fields import JSONField, config_property
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.storage import UploadedFileStorage, upload_path
from postdoc.choices import TYPE_CHOICES, WORK_ELIGIBILITY_STATUS_CHOICES, WORK_HOURS_CHOICES


def postdoc_attachment_upload_to(instance, filename):
    return upload_path('postdocattachments', filename)


class PostDocAttachmentQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)

class PostDoc(models.Model):
    person = models.ForeignKey(Person, related_name='postdoc_person', on_delete=models.PROTECT, null=False)
    unit = models.ForeignKey(Unit, null=False,blank=False,on_delete=models.PROTECT)
    type = models.CharField(max_length=24, choices=TYPE_CHOICES)
    doctorate_completed_date = models.DateField()
    work_eligibility_status = models.CharField(max_length=24, choices=WORK_ELIGIBILITY_STATUS_CHOICES)
    relocation_reimbursement = models.BooleanField(default=False)
    relocation_reimbursement_amount = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    involved_teaching = models.BooleanField(default=False)
    other_info = models.CharField(max_length=500, blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField()
    benefits_estimation = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    work_hours = models.CharField(max_length=16, default='FULL_TIME', choices=WORK_HOURS_CHOICES)
    hours_of_work = models.DecimalField(max_digits=5, decimal_places=2, default=35)
    vacation_entitlement_weeks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    annual_salary_amount = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    lump_sum_payment = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    admin_notes = models.CharField(max_length=1000, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)
    last_updated_at = models.DateTimeField(auto_now=True)
    last_updater = models.ForeignKey(Person, related_name='postdoc_last_updater', default=None, on_delete=models.PROTECT, null=True, editable=False)
    config = JSONField(null=False, blank=False, default=dict)

    def autoslug(self):
        if self.person.userid:
            ident = self.person.userid
        else:
            ident = str(self.person.emplid)
        return make_slug('pdf' + '-' + str(self.start_date.year) + '-' + ident)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    class Meta:
        ordering = ['person__last_name', 'person__first_name']

    def get_absolute_url(self):
        return reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': self.slug})

    def has_attachments(self):
        return self.attachments.visible().exists()

    def __str__(self):
        return "postdoc: " + str(self.person) + " in " + str(self.unit)

class PostDocSupervisor(models.Model):
    postdoc = models.ForeignKey(PostDoc, related_name='supervisor_links', on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Person, related_name='postdoc_supervisor_links', on_delete=models.PROTECT)

    class Meta:
        ordering = ('id',)
        unique_together = (('postdoc', 'supervisor'),)

    def __str__(self):
        return str(self.postdoc) + " is supervised by " + str(self.supervisor)

class PostDocFundingSource(models.Model):
    postdoc = models.ForeignKey(PostDoc, related_name='funding_sources', on_delete=models.CASCADE)
    unit = models.IntegerField(default=0)
    fund = models.IntegerField(default=0)
    project = models.CharField(max_length=10, default='', blank=True)
    amount = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return "funding source for " + str(self.postdoc) + ": " + str(self.unit) + "/" + str(self.fund) + "/" + str(self.project)


class PostDocAttachment(models.Model):
    appt = models.ForeignKey(PostDoc, null=False, blank=False, related_name='attachments', on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('appt',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=postdoc_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = PostDocAttachmentQueryset.as_manager()

    class Meta:
        ordering = ('created_at',)
        unique_together = (('appt', 'slug'),)

    def __str__(self):
        return self.contents.name + ' titled ' + self.title + ', for ' + str(self.appt)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()
