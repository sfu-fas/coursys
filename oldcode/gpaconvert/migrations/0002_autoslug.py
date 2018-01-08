# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('gpaconvert', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradesource',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'_auto_slug', editable=False),
        ),
    ]
