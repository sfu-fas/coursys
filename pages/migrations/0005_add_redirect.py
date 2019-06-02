# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0004_add_pagepermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageversion',
            name='redirect',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
    ]
