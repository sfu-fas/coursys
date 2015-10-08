# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0007_auto_20151006_1307'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='futureperson',
            name='email',
        ),
    ]
