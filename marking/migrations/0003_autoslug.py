# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0002_longer_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitycomponent',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'numeric_activity',), editable=False),
        ),
    ]
