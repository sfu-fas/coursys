# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import outreach.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0013_auto_20160531_1320'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutreachEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60)),
                ('start_date', models.DateTimeField(default=outreach.models.timezone_today, help_text=b'Event start date and time.  Use 24h format for the time if needed.', verbose_name=b'Start Date and Time')),
                ('end_date', models.DateTimeField(help_text=b'Event end date and time, if any', null=True, verbose_name=b'End Date and Time', blank=True)),
                ('description', models.CharField(max_length=400, null=True, blank=True)),
                ('score', models.DecimalField(max_length=2, null=True, max_digits=2, decimal_places=0, blank=True)),
                ('resources', models.CharField(help_text=b'Resources needed for this event.', max_length=400, null=True, blank=True)),
                ('cost', models.DecimalField(help_text=b'Cost of this event', null=True, max_digits=8, decimal_places=2, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='OutreachEventRegistration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('last_name', models.CharField(max_length=32, verbose_name=b'Participant Last Name')),
                ('first_name', models.CharField(max_length=32, verbose_name=b'Participant First Name')),
                ('middle_name', models.CharField(max_length=32, null=True, verbose_name=b'Participant Middle Name', blank=True)),
                ('age', models.DecimalField(null=True, verbose_name=b'Participant Age', max_digits=2, decimal_places=0, blank=True)),
                ('contact', models.CharField(max_length=400, null=True, verbose_name=b'Emergency Contact', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name=b'Contact E-mail')),
                ('waiver', models.BooleanField(default=False, help_text=b'I agree to have <insert legalese here>')),
                ('school', models.CharField(max_length=200, null=True, verbose_name=b'Participant School', blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('notes', models.CharField(max_length=400, null=True, verbose_name=b'Special Instructions', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(editable=False)),
                ('attended', models.BooleanField(default=True, editable=False)),
                ('event', models.ForeignKey(to='outreach.OutreachEvent')),
            ],
        ),
    ]
