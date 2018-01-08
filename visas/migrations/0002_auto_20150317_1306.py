# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('visas', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visa',
            name='end_date',
            field=models.DateField(verbose_name=b'End Date', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='visa',
            name='start_date',
            field=models.DateField(default=datetime.date(2015, 3, 17), verbose_name=b'Start Date'),
            preserve_default=True,
        ),
    ]
