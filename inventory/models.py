"""
A module written for inventory control of any type of asset we may want.
"""

import os
from coredata.models import Unit, Person
from outreach.models import OutreachEvent
from autoslug import AutoSlugField
from django.db import models
from django.utils import timezone
from django.forms import ValidationError
from dateutil import parser
from courselib.slugs import make_slug
from courselib.json_fields import JSONField
from courselib.storage import UploadedFileStorage, upload_path
from courselib.search import find_userid_or_emplid
from log.models import LogEntry


CATEGORY_CHOICES = {
    ('SWAG', 'Swag'),
    ('BROC', 'Brochures'),
    ('EVEN', 'Events'),
    ('GEN', 'General'),
    ('OFF', 'Office Supplies'),
    ('TEAC', 'Teaching'),
    ('RESR', 'Research'),
    ('ADMN', 'Admin Support'),
    ('TECH', 'Tech Support'),
    ('PPE', 'PPE')
}

STOCK_STATUS_CHOICES = {
    (0, "Out of stock"),
    (1, "Low Stock"),
    (2, "In Stock"),
    (3, "Unknown"),
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
    user = models.ForeignKey(Person, blank=True, null=True, help_text="If this item is assigned to a particular user,"
                                                                      "please add them here.", on_delete=models.PROTECT)
    date_shipped = models.DateField("Date Shipped/Delivered", null=True, blank=True)
    in_use = models.BooleanField("Currently in Use", default=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified = models.DateTimeField(editable=False, blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    stock_status = models.DecimalField(max_digits=1, decimal_places=0, choices=STOCK_STATUS_CHOICES, blank=True,
                                       null=True, editable=True)
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
        self.set_stock_status()
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

    def set_stock_status(self):
        if self.out_of_stock():
            self.stock_status = 0
        elif self.needs_reorder():
            self.stock_status = 1
        elif self.in_stock():
            self.stock_status = 2
        else:
            self.stock_status = 3

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
    event = models.CharField(max_length=400, null=True, blank=True, help_text="If this change is associated with an "
                                                                              "event, fill in the event name here.")
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


# Helper method to both check and add inventory items from a CSV upload
def assets_from_csv(request, data, save=False):
    # Create a unit map so we don't do a lookup for each line, since most likely all items will just be from one or two
    # units
    unit_lookup = {}

    # Create a category map, so we can map the given string to a proper category:
    category_lookup = {}
    for cat in CATEGORY_CHOICES:
        category_lookup[cat[1].upper()] = cat[0]
    # The request should still have the units for which the user has the correct role
    line_counter = 0
    ROW_LENGTH = 25
    for row in data:
        line_counter += 1
        row_length = len(row)
        if row_length != ROW_LENGTH:
            raise ValidationError("Row on line %i has %i columns, whereas it should have exactly %i." %
                                  (line_counter, row_length, ROW_LENGTH))
        # Instead of raising a validation for any over-long string, simply truncate them.
        name = row[0][:150]
        if not name:
            raise ValidationError("Line %i:  Item has no name." % line_counter)
        unit_abbrv = row[1][:4]
        if unit_abbrv in unit_lookup:
            unit = unit_lookup[unit_abbrv.upper()]
        else:
            try:
                unit = Unit.objects.get(label=unit_abbrv.upper())
            except Unit.DoesNotExist:
                raise ValidationError("Line %i: Could not find unit matching '%s'." % (line_counter, unit_abbrv))
            unit_lookup[unit_abbrv.upper()] = unit
        if unit not in request.units:
            raise ValidationError("Line %i: You do not have permission to add items for the unit %s." %
                                  (line_counter, unit.name))
        brand = row[2][:60] or None
        description = row[3][:400] or None
        serial = row[4][:60] or None
        tag = row[5][:60] or None
        express_service_code = row[6][:60] or None
        quantity_string = row[7]
        if quantity_string:
            try:
                quantity = int(quantity_string)
            except ValueError:
                raise ValidationError("Line %i: Quantity '%s' cannot be converted to an integer." %
                                      (line_counter, quantity_string))
        else:
            quantity = None
        min_qty_string = row[8]
        if min_qty_string:
            try:
                min_qty = int(min_qty_string)
            except ValueError:
                raise ValidationError("Line %i: Minimum re-order quantity '%s' cannot be converted to an integer." %
                                      (line_counter, min_qty_string))
        else:
            min_qty = None
        qty_ordered_string = row[9]
        if qty_ordered_string:
            try:
                qty_ordered = int(qty_ordered_string)
            except ValueError:
                raise ValidationError("Line %i: Quantity on order '%s' cannot be converted to an integer." %
                                      (line_counter, qty_ordered_string))
        else:
            qty_ordered = None
        min_vendor_qty_string = row[10]
        if min_vendor_qty_string:
            try:
                min_vendor_qty = int(min_vendor_qty_string)
            except ValueError:
                raise ValidationError("Line %i: Minimum vendor quantity '%s' cannot be converted to an integer." %
                                      (line_counter, min_vendor_qty_string))
        else:
            min_vendor_qty = None
        last_order_date_string = row[11]
        if last_order_date_string:
            try:
                last_order_date = parser.parse(last_order_date_string)
            except ValueError:
                raise ValidationError("Line %i: Last order date '%s' cannot be converted to proper date." %
                                      (line_counter, last_order_date_string))
        else:
            last_order_date = None
        price_string = row[12]
        if price_string:
            try:
                price = round(float(price_string), 2)
            except ValueError:
                raise ValidationError("Line %i: Price '%s' cannot be converted to proper floating decimal value." %
                                      (line_counter, price_string))

        else:
            price = None
        category_string = row[13]
        if not category_string:
            raise ValidationError("Line %i: You must provide a category for your item." % line_counter)
        if category_string.upper() in category_lookup:
            category = category_lookup[category_string.upper()]
        else:
            raise ValidationError("Line %i:  Category '%s' not found." % (line_counter, category_string))
        location = row[14][:150] or None
        po = row[15][:60]  or None
        account = row[16][:60] or None
        vendor = row[17][:400] or None
        calibration_date_string = row[18]
        if calibration_date_string:
            try:
                calibration_date = parser.parse(calibration_date_string)
            except ValueError:
                raise ValidationError("Line %i: Calibration date '%s' cannot be converted to proper date." %
                                      (line_counter, calibration_date_string))
        else:
            calibration_date = None
        eol_date_string = row[19]
        if eol_date_string:
            try:
                eol_date = parser.parse(eol_date_string)
            except ValueError:
                raise ValidationError("Line %i: End of Life date '%s' cannot be converted to proper date." %
                                      (line_counter, eol_date_string))
        else:
            eol_date = None
        notes = row[20][:400] or None
        service_records = row[21][:600] or None
        user_string = row[22]
        if user_string:
            try:
                user = Person.objects.get(find_userid_or_emplid(user_string))
            except Person.DoesNotExist:
                raise ValidationError("Line %i: User with user ID or employee ID '%s' not found." %
                                      (line_counter, user_string))
        else:
            user = None
        date_shipped_string = row[23]
        if date_shipped_string:
            try:
                date_shipped = parser.parse(date_shipped_string)
            except ValueError:
                raise ValidationError("Line %i: Date shipped '%s' cannot be converted to proper date." %
                                      (line_counter, date_shipped_string))
        else:
            date_shipped = None
        # Common things we would expect to be in the column to mean yes/true
        in_use = row[24].lower() in ("yes", "true", "y", "t", "1")

        # And now, the world's most repetitively redundant constructor, but it should hopefully be robust.
        asset = Asset(name=name, unit=unit, brand=brand, description=description, serial=serial, tag=tag,
                      express_service_code=express_service_code, quantity=quantity, min_qty=min_qty,
                      qty_ordered=qty_ordered, min_vendor_qty=min_vendor_qty, last_order_date=last_order_date,
                      price=price, category=category, location=location, po=po, account=account, vendor=vendor,
                      calibration_date=calibration_date, eol_date=eol_date, notes=notes,
                      service_records=service_records, user=user, date_shipped=date_shipped, in_use=in_use)
        if save:
            asset.save()
            l = LogEntry(userid=request.user.username,
                         description="Added asset %s via file upload." % asset.name,
                         related_object=asset)
            l.save()
    return line_counter
