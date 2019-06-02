# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0002_raappointment_visa_verified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='project',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='raappointment',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='raappointment',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
