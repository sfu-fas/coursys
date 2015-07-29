# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0004_position'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='position',
            name='teaching_load',
        ),
    ]
