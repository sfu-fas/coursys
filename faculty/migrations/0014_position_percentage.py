# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0013_auto_20160125_1103'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='percentage',
            field=models.DecimalField(decimal_places=2, default=100, max_digits=5, blank=True, help_text=b'Percentage of this position in the given unit', null=True),
        ),
    ]
