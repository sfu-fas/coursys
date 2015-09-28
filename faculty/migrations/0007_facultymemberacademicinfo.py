# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0003_remove_computingaccount'),
        ('faculty', '0006_auto_20150729_1017'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacultyMemberAcademicInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('degree1', models.CharField(max_length=12, verbose_name=b'Degree 1')),
                ('year1', models.CharField(max_length=5, verbose_name=b'Year')),
                ('institution1', models.CharField(max_length=30, verbose_name=b'Institution')),
                ('location1', models.CharField(max_length=25, verbose_name=b'City/Country')),
                ('degree2', models.CharField(max_length=12, verbose_name=b'Degree 2')),
                ('year2', models.CharField(max_length=5, verbose_name=b'Year')),
                ('institution2', models.CharField(max_length=30, verbose_name=b'Institution')),
                ('location2', models.CharField(max_length=25, verbose_name=b'City/Country')),
                ('degree3', models.CharField(max_length=12, verbose_name=b'Degree 3')),
                ('year3', models.CharField(max_length=5, verbose_name=b'Year')),
                ('institution3', models.CharField(max_length=30, verbose_name=b'Institution')),
                ('location3', models.CharField(max_length=25, verbose_name=b'City/Country')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('person', models.OneToOneField(to='coredata.Person')),
            ],
        ),
    ]
