# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0009_auto_20160118_1539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roleaccount',
            name='first_name',
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='roleaccount',
            name='last_name',
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='roleaccount',
            name='userid',
            field=models.CharField(help_text=b'SFU Unix userid (i.e. part of SFU email address before the "@").', unique=True, max_length=8, verbose_name=b'User ID', db_index=True),
        ),
    ]
