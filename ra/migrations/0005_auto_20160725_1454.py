# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0004_add_department_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='raappointment',
            name='notes',
            field=models.TextField(help_text=b'Biweekly employment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.', blank=True),
        ),
    ]
