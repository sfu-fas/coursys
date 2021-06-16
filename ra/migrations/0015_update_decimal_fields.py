# Generated by Django 2.2.15 on 2021-06-14 14:43

import django.core.files.storage
from django.db import migrations, models
import ra.models


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0014_add_file_mediatypes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rarequest',
            name='biweekly_hours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AlterField(
            model_name='rarequest',
            name='vacation_hours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
