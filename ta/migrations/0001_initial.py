# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0001_initial'),
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampusPreference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('campus', models.CharField(max_length=5, choices=[(b'BRNBY', b'Burnaby Campus'), (b'SURRY', b'Surrey Campus'), (b'VANCR', b'Harbour Centre'), (b'OFFST', b'Off-campus'), (b'GNWC', b'Great Northern Way Campus'), (b'METRO', b'Other Locations in Vancouver')])),
                ('pref', models.CharField(max_length=3, choices=[(b'PRF', b'Preferred'), (b'WIL', b'Willing'), (b'NOT', b'Not willing')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseDescription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(help_text=b"Description of the work for a course, as it will appear on the contract. (e.g. 'Office/marking')", max_length=60)),
                ('labtut', models.BooleanField(default=False, help_text=b'Does this description get the 0.17 BU bonus?', verbose_name=b'Lab/Tutorial?')),
                ('hidden', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CoursePreference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('taken', models.CharField(max_length=3, choices=[(b'YES', b'Yes: this course at SFU'), (b'SIM', b'Yes: a similar course elsewhere'), (b'KNO', b'No, but I know the course material'), (b'NO', b"No, I don't know the material well")])),
                ('exper', models.CharField(max_length=3, verbose_name=b'Experience', choices=[(b'FAM', b'Very familiar with course material'), (b'SOM', b'Somewhat familiar with course material'), (b'NOT', b'Not familiar with course material')])),
                ('rank', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('position', models.IntegerField()),
            ],
            options={
                'ordering': ['position'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkillLevel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.CharField(max_length=4, choices=[(b'EXPR', b'Expert'), (b'GOOD', b'Good'), (b'SOME', b'Some'), (b'NONE', b'None')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TAApplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.CharField(max_length=4, verbose_name=b'Program', choices=[(b'GTA1', b'Masters'), (b'GTA2', b'PhD'), (b'UTA', b'Undergrad'), (b'ETA', b'External')])),
                ('current_program', models.CharField(help_text=b'In what department are you a student (e.g. "CMPT", "ENSC", if applicable)?', max_length=100, null=True, verbose_name=b'Department', blank=True)),
                ('sin', models.CharField(help_text=b'Social insurance number (required for receiving payments)', max_length=30, verbose_name=b'SIN', blank=True)),
                ('base_units', models.DecimalField(default=5, help_text=b"Maximum number of base units (BU's) you would accept. Each BU represents a maximum of 42 hours of work for the semester. TA appointments can consist of 2 to 5 base units and are based on course enrollments and department requirements.", max_digits=4, decimal_places=2)),
                ('experience', models.TextField(help_text=b'Describe any other experience that you think may be relevant to these courses.', null=True, verbose_name=b'Additional Experience', blank=True)),
                ('course_load', models.TextField(help_text=b'Describe the intended course load of the semester being applied for.', verbose_name=b'Intended course load', blank=True)),
                ('other_support', models.TextField(help_text=b'Do you have a merit based scholarship or fellowship (e.g. FAS Graduate Fellowship) in the semester that you are applying for? ', null=True, verbose_name=b'Other financial support', blank=True)),
                ('comments', models.TextField(null=True, verbose_name=b'Additional comments', blank=True)),
                ('rank', models.IntegerField(default=0)),
                ('late', models.BooleanField(default=False)),
                ('admin_created', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TAContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'NEW', max_length=3, verbose_name=b'Appointment Status', choices=[(b'NEW', b'Draft'), (b'OPN', b'Offered'), (b'REJ', b'Rejected'), (b'ACC', b'Accepted'), (b'SGN', b'Contract Signed'), (b'CAN', b'Cancelled')])),
                ('sin', models.CharField(help_text=b'Social insurance number', max_length=30, verbose_name=b'SIN')),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('appt_category', models.CharField(default=b'GTA1', max_length=4, verbose_name=b'Appointment Category', choices=[(b'GTA1', b'Masters'), (b'GTA2', b'PhD'), (b'UTA', b'Undergrad'), (b'ETA', b'External')])),
                ('appt', models.CharField(default=b'INIT', max_length=4, verbose_name=b'Appointment', choices=[(b'INIT', b'Initial appointment to this position'), (b'REAP', b'Reappointment to same position or revision to appointment')])),
                ('pay_per_bu', models.DecimalField(verbose_name=b'Pay per Base Unit Semester Rate.', max_digits=8, decimal_places=2)),
                ('scholarship_per_bu', models.DecimalField(verbose_name=b'Scholarship per Base Unit Semester Rate.', max_digits=8, decimal_places=2)),
                ('appt_cond', models.BooleanField(default=False, verbose_name=b'Conditional')),
                ('appt_tssu', models.BooleanField(default=True, verbose_name=b'Appointment in TSSU')),
                ('deadline', models.DateField(help_text=b'Deadline for the applicant to accept/decline the offer', verbose_name=b'Acceptance Deadline')),
                ('remarks', models.TextField(blank=True)),
                ('created_by', models.CharField(max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(to='ta.TAApplication')),
                ('position_number', models.ForeignKey(to='ra.Account')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TACourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bu', models.DecimalField(max_digits=4, decimal_places=2)),
                ('contract', models.ForeignKey(to='ta.TAContract')),
                ('course', models.ForeignKey(to='coredata.CourseOffering')),
                ('description', models.ForeignKey(to='ta.CourseDescription')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TAPosting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('opens', models.DateField(help_text=b'Opening date for the posting')),
                ('closes', models.DateField(help_text=b'Closing date for the posting')),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('semester', models.ForeignKey(to='coredata.Semester')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TUG',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('base_units', models.DecimalField(max_digits=4, decimal_places=2)),
                ('last_update', models.DateField(auto_now=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('member', models.ForeignKey(to='coredata.Member', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='taposting',
            unique_together=set([('unit', 'semester')]),
        ),
        migrations.AlterUniqueTogether(
            name='tacourse',
            unique_together=set([('contract', 'course')]),
        ),
        migrations.AddField(
            model_name='tacontract',
            name='posting',
            field=models.ForeignKey(to='ta.TAPosting'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='tacontract',
            unique_together=set([('posting', 'application')]),
        ),
        migrations.AddField(
            model_name='taapplication',
            name='posting',
            field=models.ForeignKey(to='ta.TAPosting'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='taapplication',
            unique_together=set([('person', 'posting')]),
        ),
        migrations.AddField(
            model_name='skilllevel',
            name='app',
            field=models.ForeignKey(to='ta.TAApplication'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='skilllevel',
            name='skill',
            field=models.ForeignKey(to='ta.Skill'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='skill',
            name='posting',
            field=models.ForeignKey(to='ta.TAPosting'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='skill',
            unique_together=set([('posting', 'position')]),
        ),
        migrations.AddField(
            model_name='coursepreference',
            name='app',
            field=models.ForeignKey(to='ta.TAApplication'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursepreference',
            name='course',
            field=models.ForeignKey(to='coredata.Course'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='campuspreference',
            name='app',
            field=models.ForeignKey(to='ta.TAApplication'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='campuspreference',
            unique_together=set([('app', 'campus')]),
        ),
    ]
