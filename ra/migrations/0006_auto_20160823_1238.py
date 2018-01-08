# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0005_auto_20160725_1454'),
    ]

    operations = [
        migrations.AlterField(
            model_name='raappointment',
            name='comments',
            field=models.TextField(help_text=b'For internal use', verbose_name=b'Notes', blank=True),
        ),
        migrations.AlterField(
            model_name='raappointment',
            name='notes',
            field=models.TextField(help_text=b'Biweekly employment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.', verbose_name=b'Comments', blank=True),
        ),
    ]
