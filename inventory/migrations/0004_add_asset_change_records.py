# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0001_initial'),
        ('coredata', '0014_auto_20160623_1509'),
        ('inventory', '0003_auto_20160728_1402'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetChangeRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('qty', models.IntegerField(help_text=b"The change in quantity.  For removal of item, make it a negative number. For adding items, make it a positive.  e.g. '-2' if someone removed two ofthis item for something", verbose_name=b'Quantity adjustment')),
                ('date', models.DateField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('saved_by_userid', models.CharField(max_length=8, editable=False)),
                ('config', courselib.json_fields.JSONField(default=dict, editable=False)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
            ],
        ),
        migrations.AddField(
            model_name='asset',
            name='config',
            field=courselib.json_fields.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='asset',
            name='last_order_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='min_vendor_qty',
            field=models.PositiveIntegerField(help_text=b'The minimum quantity the vendor will let us order', null=True, verbose_name=b'Minimum vendor order quantity', blank=True),
        ),
        migrations.AddField(
            model_name='assetchangerecord',
            name='asset',
            field=models.ForeignKey(to='inventory.Asset'),
        ),
        migrations.AddField(
            model_name='assetchangerecord',
            name='event',
            field=models.ForeignKey(help_text=b'The event it was for, if any', to='outreach.OutreachEvent'),
        ),
        migrations.AddField(
            model_name='assetchangerecord',
            name='person',
            field=models.ForeignKey(to='coredata.Person'),
        ),
    ]
