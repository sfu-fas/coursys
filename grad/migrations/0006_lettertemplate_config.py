# -*- coding: utf-8 -*-


from django.db import migrations, models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0005_auto_20160311_1155'),
    ]

    operations = [
        migrations.AddField(
            model_name='lettertemplate',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
    ]
