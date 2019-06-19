"""
A module written for inventory control of any type of asset we may want.
"""

import os
from coredata.models import Unit, Person
from outreach.models import OutreachEvent
from autoslug import AutoSlugField
from django.db import models
from django.utils import timezone
from courselib.slugs import make_slug
from courselib.json_fields import JSONField
from courselib.storage import UploadedFileStorage, upload_path


CATEGORY_CHOICES = {
    ('SWAG', 'Swag'),
    ('DISP', 'Display'),
    ('BANN', 'Banners'),
    ('BROC', 'Brochures'),
    ('EVEN', 'Events'),
    ('GEN', 'General'),
    ('OFF', 'Office Supplies'),
    ('SURP', 'Surplus'),
    ('TEAC', 'Teaching'),
    ('RESR', 'Research'),
    ('ADMN', 'Admin Support'),
    ('TECH', 'Tech Support'),
}


class AssetQuerySet(models.QuerySet):
    """
    Only see visible items, in this case also limited by accessible units.
    """
    def visible(self, units):
        return self.filter(hidden=False, unit__in=units)


class Asset(models.Model):
    name = models.CharField(max_length=150, null=False, blank=False)
    unit = models.ForeignKey(Unit, blank=False, null=False, help_text='Unit to which this asset belongs', on_delete=models.PROTECT)
    brand = models.CharField(max_length=60, null=True, blank=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    serial = models.CharField("Serial Number", max_length=60, null=True, blank=True)
    tag = models.CharField("Service Tag", max_length=60, null=True, blank=True, help_text="Service Tag, or SFU Asset "
                                                                                          "Tag number, if it exists")
    express_service_code = models.CharField(max_length=60, null=True, blank=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    min_qty = models.PositiveIntegerField("Minimum re-order quantity", blank=True, null=True,
                                          help_text="The minimum quantity that should be in stock before having to "
                                                    "re-order")
    qty_ordered = models.PositiveIntegerField("Quantity on order", blank=True, null=True)
    min_vendor_qty = models.PositiveIntegerField("Minimum vendor order quantity", blank=True, null=True,
                                                 help_text="The minimum quantity the vendor will let us order")
    last_order_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, null=True, blank=True, default='GEN')
    location = models.CharField(max_length=150, null=True, blank=True)
    po = models.CharField("PR/PO No.", max_length=60, null=True, blank=True)
    account = models.CharField("Account No.", max_length=60, null=True, blank=True)
    vendor = models.CharField("Supplier/Vendor", max_length=400, null=True, blank=True)
    calibration_date = models.DateField("Calibration/Service Date", null=True, blank=True)
    eol_date = models.DateField("End of Life Date", null=True, blank=True)
    notes = models.CharField(max_length=400, null=True, blank=True)
    service_records = models.CharField(max_length=600, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified = models.DateTimeField(editable=False, blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    # In case we forgot something, this will make it easier to add something in the future without a migration.
    config = JSONField(null=False, blank=False, default=dict, editable=False)

    objects = AssetQuerySet.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.name)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __str__(self):
        return "%s - %s" % (self.name, self.unit.label)

    def save(self, *args, **kwargs):
        self.last_modified = timezone.now()
        super(Asset, self).save(*args, **kwargs)

    def delete(self):
        """
        Like most of our objects, never actually delete them, just hide them.
        """
        self.hidden = True
        self.save()

    #  Some helper methods to display things with a color code in the index list.
    def out_of_stock(self):
        return self.quantity is not None and self.quantity == 0

    def needs_reorder(self):
        return self.quantity is not None and self.min_qty is not None and self.quantity <= self.min_qty

    def in_stock(self):
        return self.quantity is not None and self.min_qty is not None and self.quantity > self.min_qty

    def has_attachments(self):
        return self.attachments.visible().count() > 0

    def has_records(self):
        return self.records.visible().count() > 0


class AssetChangeRecordQuerySet(models.QuerySet):
    """
    Only see visible items, in this case also limited by a given asset.
    """
    def visible(self):
        return self.filter(hidden=False)


class AssetChangeRecord(models.Model):
    asset = models.ForeignKey(Asset, null=False, blank=False, related_name='records', on_delete=models.PROTECT)
    person = models.ForeignKey(Person, null=False, blank=False, on_delete=models.PROTECT)
    qty = models.IntegerField("Quantity adjustment", null=False, blank=False,
                              help_text="The change in quantity.  For removal of item, make it a negative number. "
                                        "For adding items, make it a positive.  e.g. '-2' if someone removed two of "
                                        "this item for something")
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified = models.DateTimeField(editable=False, blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    saved_by_userid = models.CharField(max_length=8, blank=False, null=False, editable=False)
    # In case we forgot something, this will make it easier to add something in the future without a migration.
    config = JSONField(null=False, blank=False, default=dict, editable=False)

    def autoslug(self):
        if self.qty > 0:
            change_string=" added "
        else:
            change_string=" removed "
        return make_slug(self.person.userid_or_emplid() + change_string + str(self.qty) + ' ' + str(self.asset))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    objects = AssetChangeRecordQuerySet.as_manager()

    def save(self, user, *args, **kwargs):
        self.last_modified = timezone.now()
        self.saved_by_userid = user
        super(AssetChangeRecord, self).save(*args, **kwargs)

    def delete(self, user):
        """
        Like most of our objects, never actually delete them, just hide them.
        """
        self.hidden = True
        self.save(user)


def asset_attachment_upload_to(instance, filename):
    return upload_path('assets', filename)


class AssetDocumentAttachmentQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)


class AssetDocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    asset = models.ForeignKey(Asset, null=False, blank=False, related_name="attachments", on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('asset',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=asset_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = AssetDocumentAttachmentQueryset.as_manager()

    def __str__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("asset", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()
