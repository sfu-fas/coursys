# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissioncomponent',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'activity',), editable=False),
        ),
    ]
