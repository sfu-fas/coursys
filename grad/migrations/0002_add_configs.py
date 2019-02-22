# -*- coding: utf-8 -*-


from django.db import models, migrations
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradprogramhistory',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gradstatus',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
            preserve_default=True,
        ),
    ]
