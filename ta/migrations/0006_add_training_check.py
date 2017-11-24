# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-10-27 14:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ta', '0005_auto_20160620_1454'),
    ]

    operations = [
        migrations.AddField(
            model_name='taapplication',
            name='new_workers_training',
            field=models.BooleanField(default=False, help_text=b'WorkSafe BC requires all new employees to take a safety orientation.  SFU has a short online module you can take here <https://canvas.sfu.ca/enroll/RR8WDW> and periodically offers classroom sessions of the same material.  Some research and instructional laboratories may require additional training, contact the faculty member in charge of your lab(s) for details.', verbose_name=b'I have completed the mandatory SFU Safety Orientation training.'),
        ),
    ]