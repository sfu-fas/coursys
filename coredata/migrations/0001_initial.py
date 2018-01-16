# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import bitfield.models
import courselib.conditional_save
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CombinedOffering',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject', models.CharField(max_length=4)),
                ('number', models.CharField(max_length=4)),
                ('section', models.CharField(max_length=4)),
                ('component', models.CharField(max_length=3, choices=[(b'LEC', b'Lecture'), (b'LAB', b'Lab'), (b'TUT', b'Tutorial'), (b'SEM', b'Seminar'), (b'SEC', b'Section'), (b'PRA', b'Practicum'), (b'IND', b'Individual Work'), (b'INS', b'INS'), (b'WKS', b'Workshop'), (b'FLD', b'Field School'), (b'STD', b'Studio'), (b'OLC', b'OLC'), (b'RQL', b'RQL'), (b'STL', b'STL'), (b'CNV', b'CNV'), (b'OPL', b'Open Lab'), (b'CAN', b'Cancelled')])),
                ('instr_mode', models.CharField(default=b'P', max_length=2, choices=[(b'CO', b'Co-Op'), (b'DE', b'Distance Education'), (b'GI', b'Graduate Internship'), (b'P', b'In Person'), (b'PO', b'In Person - Off Campus')])),
                ('crse_id', models.PositiveSmallIntegerField(null=True)),
                ('class_nbr', models.PositiveIntegerField(null=True)),
                ('title', models.CharField(max_length=30)),
                ('campus', models.CharField(max_length=5, choices=[(b'BRNBY', b'Burnaby Campus'), (b'SURRY', b'Surrey Campus'), (b'VANCR', b'Harbour Centre'), (b'OFFST', b'Off-campus'), (b'GNWC', b'Great Northern Way Campus'), (b'METRO', b'Other Locations in Vancouver')])),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ComputingAccount',
            fields=[
                ('emplid', models.PositiveIntegerField(unique=True, serialize=False, primary_key=True)),
                ('userid', models.CharField(unique=True, max_length=8, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject', models.CharField(help_text=b'Subject code, like "CMPT" or "FAN".', max_length=4, db_index=True)),
                ('number', models.CharField(help_text=b'Course number, like "120" or "XX1".', max_length=4, db_index=True)),
                ('title', models.CharField(help_text=b'The course title.', max_length=30)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
            ],
            options={
                'ordering': ('subject', 'number'),
            },
            bases=(models.Model, courselib.conditional_save.ConditionalSaveMixin),
        ),
        migrations.CreateModel(
            name='CourseOffering',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject', models.CharField(help_text=b'Subject code, like "CMPT" or "FAN"', max_length=4, db_index=True)),
                ('number', models.CharField(help_text=b'Course number, like "120" or "XX1"', max_length=4, db_index=True)),
                ('section', models.CharField(help_text=b'Section should be in the form "C100" or "D100"', max_length=4, db_index=True)),
                ('component', models.CharField(help_text=b'Component of the offering, like "LEC" or "LAB"', max_length=3, db_index=True, choices=[(b'LEC', b'Lecture'), (b'LAB', b'Lab'), (b'TUT', b'Tutorial'), (b'SEM', b'Seminar'), (b'SEC', b'Section'), (b'PRA', b'Practicum'), (b'IND', b'Individual Work'), (b'INS', b'INS'), (b'WKS', b'Workshop'), (b'FLD', b'Field School'), (b'STD', b'Studio'), (b'OLC', b'OLC'), (b'RQL', b'RQL'), (b'STL', b'STL'), (b'CNV', b'CNV'), (b'OPL', b'Open Lab'), (b'CAN', b'Cancelled')])),
                ('instr_mode', models.CharField(default=b'P', help_text=b'The instructional mode of the offering', max_length=2, db_index=True, choices=[(b'CO', b'Co-Op'), (b'DE', b'Distance Education'), (b'GI', b'Graduate Internship'), (b'P', b'In Person'), (b'PO', b'In Person - Off Campus')])),
                ('graded', models.BooleanField(default=True)),
                ('crse_id', models.PositiveSmallIntegerField(null=True, db_index=True)),
                ('class_nbr', models.PositiveIntegerField(null=True, db_index=True)),
                ('title', models.CharField(help_text=b'The course title', max_length=30, db_index=True)),
                ('campus', models.CharField(db_index=True, max_length=5, choices=[(b'BRNBY', b'Burnaby Campus'), (b'SURRY', b'Surrey Campus'), (b'VANCR', b'Harbour Centre'), (b'OFFST', b'Off-campus'), (b'GNWC', b'Great Northern Way Campus'), (b'METRO', b'Other Locations in Vancouver')])),
                ('enrl_cap', models.PositiveSmallIntegerField()),
                ('enrl_tot', models.PositiveSmallIntegerField()),
                ('wait_tot', models.PositiveSmallIntegerField()),
                ('units', models.PositiveSmallIntegerField(help_text=b'The number of credits received by (most?) students in the course', null=True)),
                ('flags', bitfield.models.BitField([b'write', b'quant', b'bhum', b'bsci', b'bsoc', b'combined'], default=0)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('course', models.ForeignKey(to='coredata.Course')),
            ],
            options={
                'ordering': ['-semester', 'subject', 'number', 'section'],
            },
            bases=(models.Model, courselib.conditional_save.ConditionalSaveMixin),
        ),
        migrations.CreateModel(
            name='Holiday',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(help_text=b'Date of the holiday', db_index=True)),
                ('description', models.CharField(help_text=b'Description of holiday, e.g. "Canada Day"', max_length=30)),
                ('holiday_type', models.CharField(help_text=b'Type of holiday: how does it affect schedules?', max_length=4, choices=[(b'FULL', b'Classes cancelled, offices closed'), (b'CLAS', b'Classes cancelled, offices open'), (b'OPEN', b'Classes as scheduled')])),
            ],
            options={
                'ordering': ['date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MeetingTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('weekday', models.PositiveSmallIntegerField(help_text=b'Day of week of the meeting', choices=[(0, b'Monday'), (1, b'Tuesday'), (2, b'Wednesday'), (3, b'Thursday'), (4, b'Friday'), (5, b'Saturday'), (6, b'Sunday')])),
                ('start_time', models.TimeField(help_text=b'Start time of the meeting')),
                ('end_time', models.TimeField(help_text=b'End time of the meeting')),
                ('start_day', models.DateField(help_text=b'Starting day of the meeting')),
                ('end_day', models.DateField(help_text=b'Ending day of the meeting')),
                ('room', models.CharField(help_text=b'Room (or other location) for the meeting', max_length=20)),
                ('exam', models.BooleanField(default=False)),
                ('meeting_type', models.CharField(default=b'LEC', max_length=4, choices=[(b'LEC', b'Lecture'), (b'MIDT', b'Midterm Exam'), (b'EXAM', b'Exam'), (b'LAB', b'Lab/Tutorial')])),
                ('labtut_section', models.CharField(help_text=b'Section should be in the form "C101" or "D103".  None/blank for the non lab/tutorial events.', max_length=4, null=True, blank=True)),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
            ],
            options={
                'ordering': ['weekday'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(max_length=4, choices=[(b'STUD', b'Student'), (b'TA', b'TA'), (b'INST', b'Instructor'), (b'APPR', b'Grade Approver'), (b'DROP', b'Dropped')])),
                ('credits', models.PositiveSmallIntegerField(default=3, help_text=b'Number of credits this course is worth.')),
                ('career', models.CharField(max_length=4, choices=[(b'UGRD', b'Undergraduate'), (b'GRAD', b'Graduate'), (b'NONS', b'Non-Student')])),
                ('added_reason', models.CharField(db_index=True, max_length=4, choices=[(b'AUTO', b'Automatically added'), (b'TRU', b'TRU/OU Distance Student'), (b'CTA', b'CourSys-Appointed TA'), (b'TAC', b'CourSys-Appointed TA'), (b'TA', b'Additional TA'), (b'TAIN', b'TA added by instructor'), (b'INST', b'Additional Instructor'), (b'UNK', b'Unknown/Other Reason')])),
                ('labtut_section', models.CharField(help_text=b'Section should be in the form "C101" or "D103".', max_length=4, null=True, blank=True)),
                ('official_grade', models.CharField(max_length=2, null=True, blank=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
            ],
            options={
                'ordering': ['offering', 'person'],
            },
            bases=(models.Model, courselib.conditional_save.ConditionalSaveMixin),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('emplid', models.PositiveIntegerField(help_text=b'Employee ID (i.e. student number)', unique=True, verbose_name=b'ID #', db_index=True)),
                ('userid', models.CharField(null=True, max_length=8, blank=True, help_text=b'SFU Unix userid (i.e. part of SFU email address before the "@").', unique=True, verbose_name=b'User ID', db_index=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('middle_name', models.CharField(max_length=32, null=True, blank=True)),
                ('pref_first_name', models.CharField(max_length=32, null=True, blank=True)),
                ('title', models.CharField(max_length=4, null=True, blank=True)),
                ('temporary', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
                'ordering': ['last_name', 'first_name', 'userid'],
                'verbose_name_plural': 'People',
            },
            bases=(models.Model, courselib.conditional_save.ConditionalSaveMixin),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(max_length=4, choices=[(b'ADVS', b'Advisor'), (b'FAC', b'Faculty Member'), (b'SESS', b'Sessional Instructor'), (b'COOP', b'Co-op Staff'), (b'INST', b'Other Instructor'), (b'SUPV', b'Additional Supervisor'), (b'PLAN', b'Planning Administrator'), (b'DISC', b'Discipline Case Administrator'), (b'DICC', b'Discipline Case Filer (email CC)'), (b'ADMN', b'Departmental Administrator'), (b'TAAD', b'TA Administrator'), (b'TADM', b'Teaching Administrator'), (b'GRAD', b'Grad Student Administrator'), (b'GRPD', b'Graduate Program Director'), (b'FUND', b'Grad Funding Administrator'), (b'TECH', b'Tech Staff'), (b'GPA', b'GPA conversion system admin'), (b'SYSA', b'System Administrator'), (b'NONE', b'none')])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Semester name should be in the form "1097".', unique=True, max_length=4, db_index=True)),
                ('start', models.DateField(help_text=b'First day of classes.')),
                ('end', models.DateField(help_text=b'Last day of classes.')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SemesterWeek',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('week', models.PositiveSmallIntegerField(help_text=b'Week of the semester (typically 1-13)')),
                ('monday', models.DateField(help_text=b'Monday of this week.')),
                ('semester', models.ForeignKey(to='coredata.Semester')),
            ],
            options={
                'ordering': ['semester', 'week'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(help_text=b"The unit code, e.g. 'CMPT'.", unique=True, max_length=4, db_index=True)),
                ('name', models.CharField(help_text=b"The full name of the unit, e.g. 'School of Computing Science'.", max_length=60)),
                ('acad_org', models.CharField(null=True, max_length=10, blank=True, help_text=b'ACAD_ORG field from SIMS', unique=True, db_index=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('parent', models.ForeignKey(blank=True, to='coredata.Unit', help_text=b'Next unit up in the hierarchy.', null=True)),
            ],
            options={
                'ordering': ['label'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='semesterweek',
            unique_together=set([('semester', 'week')]),
        ),
        migrations.AddField(
            model_name='role',
            name='unit',
            field=models.ForeignKey(to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='role',
            unique_together=set([('person', 'role', 'unit')]),
        ),
        migrations.AddField(
            model_name='member',
            name='person',
            field=models.ForeignKey(related_name='person', to='coredata.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='holiday',
            name='semester',
            field=models.ForeignKey(to='coredata.Semester'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='members',
            field=models.ManyToManyField(related_name='member', through='coredata.Member', to='coredata.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='owner',
            field=models.ForeignKey(to='coredata.Unit', help_text=b'Unit that controls this offering', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='semester',
            field=models.ForeignKey(to='coredata.Semester'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='courseoffering',
            unique_together=set([('semester', 'crse_id', 'section'), ('semester', 'subject', 'number', 'section'), ('semester', 'class_nbr')]),
        ),
        migrations.AlterUniqueTogether(
            name='course',
            unique_together=set([('subject', 'number')]),
        ),
        migrations.AddField(
            model_name='combinedoffering',
            name='offerings',
            field=models.ManyToManyField(related_name='+', to='coredata.CourseOffering'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='combinedoffering',
            name='owner',
            field=models.ForeignKey(to='coredata.Unit', help_text=b'Unit that controls this offering', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='combinedoffering',
            name='semester',
            field=models.ForeignKey(to='coredata.Semester'),
            preserve_default=True,
        ),
    ]
