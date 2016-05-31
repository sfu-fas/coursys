# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
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
                ('start_date', models.DateField(default=outreach.models.timezone_today, help_text=b'Event start date', verbose_name=b'Start Date')),
                ('end_date', models.DateField(help_text=b'Event end date, if any', null=True, verbose_name=b'End Date', blank=True)),
                ('description', models.CharField(max_length=400, null=True, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='OutreachEventRegistration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('middle_name', models.CharField(max_length=32, null=True, blank=True)),
                ('email', models.EmailField(max_length=254)),
                ('waiver', models.BooleanField(default=False, help_text=b'I agree to have <insert legalese here>')),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('event', models.ForeignKey(to='outreach.OutreachEvent')),
            ],
        ),
    ]
