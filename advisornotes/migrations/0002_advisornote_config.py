# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('advisornotes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='advisornote',
            name='config',
            field=courselib.json_fields.JSONField(default={}),
            preserve_default=True,
        ),
    ]
