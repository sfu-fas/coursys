# Generated by Django 3.2.15 on 2023-06-22 10:48

import courselib.json_fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ta', '0013_auto_20230103_1440'),
    ]

    operations = [
        migrations.AddField(
            model_name='tacontract',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
    ]
