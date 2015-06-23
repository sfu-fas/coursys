# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('advisornotes', '0004_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artifact',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='nonstudent',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
