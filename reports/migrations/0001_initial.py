# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        #('alerts', '__first__'),
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('notify', models.BooleanField(default=False, help_text=b'Email this person when a report completes.')),
                ('config', courselib.json_fields.JSONField(default={})),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HardcodedReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file_location', models.CharField(help_text=b'The location of this report, on disk.', max_length=80, choices=[(b'majors_in_courses.py', b'majors_in_courses.py'), (b'enscpro_coop.py', b'enscpro_coop.py'), (b'bad_first_semester.py', b'bad_first_semester.py'), (b'five_retakes.py', b'five_retakes.py'), (b'bad_gpas.py', b'bad_gpas.py'), (b'ensc_150_and_250_but_not_215.py', b'ensc_150_and_250_but_not_215.py'), (b'fas_international.py', b'fas_international.py'), (b'fas_with_email.py', b'fas_with_email.py'), (b'immediate_retake_report.py', b'immediate_retake_report.py'), (b'fake_report.py', b'fake_report.py'), (b'cmpt165_after_cmpt.py', b'cmpt165_after_cmpt.py')])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Query',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('query', models.TextField()),
                ('config', courselib.json_fields.JSONField(default={})),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Name of the report.', max_length=150)),
                ('description', models.TextField(help_text=b'Description of the report.', null=True, blank=True)),
                ('hidden', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                #('alert', models.ForeignKey(to='alerts.AlertType', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('table', courselib.json_fields.JSONField(default={})),
                ('config', courselib.json_fields.JSONField(default={})),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Run',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=150)),
                ('success', models.BooleanField(default=False)),
                ('manual', models.BooleanField(default=False, help_text=b'Was this run requested manually (as opposed to scheduled)?')),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('report', models.ForeignKey(to='reports.Report')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RunLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField()),
                ('run', models.ForeignKey(to='reports.Run')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScheduleRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('schedule_type', models.CharField(default=b'ONE', max_length=3, choices=[(b'ONE', b'One-Time'), (b'DAI', b'Daily'), (b'MON', b'Monthly'), (b'YEA', b'Yearly')])),
                ('last_run', models.DateTimeField(null=True)),
                ('next_run', models.DateTimeField()),
                ('config', courselib.json_fields.JSONField(default={})),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.ForeignKey(to='reports.Report')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='result',
            name='run',
            field=models.ForeignKey(to='reports.Run'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='query',
            name='report',
            field=models.ForeignKey(to='reports.Report'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hardcodedreport',
            name='report',
            field=models.ForeignKey(to='reports.Report'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accessrule',
            name='report',
            field=models.ForeignKey(to='reports.Report'),
            preserve_default=True,
        ),
    ]
