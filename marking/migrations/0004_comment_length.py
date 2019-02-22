# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0003_autoslug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitycomponent',
            name='description',
            field=models.TextField(max_length=5000, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='activitymark',
            name='mark_adjustment_reason',
            field=models.TextField(max_length=5000, null=True, verbose_name=b'Mark Penalty Reason', blank=True),
        ),
        migrations.AlterField(
            model_name='activitymark',
            name='overall_comment',
            field=models.TextField(max_length=5000, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='activitymark_lettergrade',
            name='overall_comment',
            field=models.TextField(max_length=5000, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='commonproblem',
            name='description',
            field=models.TextField(max_length=5000, null=True, blank=True),
        ),
    ]
