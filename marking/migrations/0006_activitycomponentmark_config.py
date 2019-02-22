# -*- coding: utf-8 -*-


from django.db import migrations, models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0005_auto_20151029_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitycomponentmark',
            name='config',
            field=courselib.json_fields.JSONField(default={}),
        ),
    ]
