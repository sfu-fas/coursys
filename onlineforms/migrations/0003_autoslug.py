# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('onlineforms', '0002_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='field',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'sheet',), editable=False),
        ),
        migrations.AlterField(
            model_name='form',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='form',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='formgroup',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='formgroup',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'form',), editable=False),
        ),
        migrations.AlterField(
            model_name='sheet',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='sheet',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'form',), editable=False),
        ),
        migrations.AlterField(
            model_name='sheetsubmission',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='sheetsubmission',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'form_submission',), editable=False),
        ),
    ]
