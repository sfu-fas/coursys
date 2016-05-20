# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):


    operations = [
        migrations.CreateModel(
            name='SessionalAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60)),
                ('account_number', models.PositiveIntegerField()),
                ('position_number', models.PositiveIntegerField()),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='SessionalContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('appointment_start', models.DateField(null=True, blank=True)),
                ('appointment_end', models.DateField(null=True, blank=True)),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.CharField(max_length=20, editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('config', courselib.json_fields.JSONField(default=dict, editable=False)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('account', models.ForeignKey(to='sessionals.SessionalAccount')),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
                ('sessional', models.ForeignKey(to='coredata.AnyPerson')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='sessionalcontract',
            unique_together=set([('sessional', 'account', 'offering')]),
        ),
    ]
