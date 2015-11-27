# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_update_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='result',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='run',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
