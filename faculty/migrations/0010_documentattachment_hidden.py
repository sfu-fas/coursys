# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0009_auto_20151106_1716'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentattachment',
            name='hidden',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
