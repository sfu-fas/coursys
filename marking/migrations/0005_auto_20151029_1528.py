# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0004_comment_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitycomponentmark',
            name='value',
            field=models.DecimalField(null=True, verbose_name=b'Mark', max_digits=8, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='activitymark',
            name='mark',
            field=models.DecimalField(null=True, max_digits=8, decimal_places=2),
        ),
    ]
