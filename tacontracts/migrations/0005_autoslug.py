# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('tacontracts', '0004_tacontract_visa_verified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tacategory',
            name='config',
            field=courselib.json_fields.JSONField(default=dict, editable=False),
        ),
        migrations.AlterField(
            model_name='tacategory',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='tacontract',
            name='config',
            field=courselib.json_fields.JSONField(default=dict, editable=False),
        ),
        migrations.AlterField(
            model_name='tacontract',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='tacourse',
            name='config',
            field=courselib.json_fields.JSONField(default=dict, editable=False),
        ),
        migrations.AlterField(
            model_name='tacourse',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', editable=False),
        ),
    ]
