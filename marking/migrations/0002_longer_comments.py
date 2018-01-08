# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitycomponent',
            name='description',
            field=models.TextField(max_length=500, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='commonproblem',
            name='description',
            field=models.TextField(max_length=500, null=True, blank=True),
            preserve_default=True,
        ),
    ]
