# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('ta', '0002_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taposting',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='taposting',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
