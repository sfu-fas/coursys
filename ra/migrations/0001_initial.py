# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0001_initial'),
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('account_number', models.PositiveIntegerField()),
                ('position_number', models.PositiveIntegerField()),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('hidden', models.BooleanField(default=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
                'ordering': ['account_number'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project_number', models.PositiveIntegerField()),
                ('fund_number', models.PositiveIntegerField()),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('hidden', models.BooleanField(default=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
                'ordering': ['project_number'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RAAppointment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sin', models.PositiveIntegerField(null=True, blank=True)),
                ('hiring_category', models.CharField(default=b'GRA', max_length=4, choices=[(b'U', b'Undergrad'), (b'E', b'Grad Employee'), (b'N', b'Non-Student'), (b'S', b'Grad Scholarship'), (b'RA', b'Research Assistant'), (b'RSS', b'Research Services Staff'), (b'PDF', b'Post Doctoral Fellow'), (b'ONC', b'Other Non Continuing'), (b'RA2', b'University Research Assistant (Min of 2 years with Benefits)'), (b'RAR', b'University Research Assistant (Renewal after 2 years with Benefits)'), (b'GRA', b'Graduate Research Assistant'), (b'NS', b'National Scholarship')])),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('pay_frequency', models.CharField(default=b'B', max_length=60, choices=[(b'B', b'Biweekly'), (b'L', b'Lump Sum')])),
                ('lump_sum_pay', models.DecimalField(verbose_name=b'Total Pay', max_digits=8, decimal_places=2)),
                ('lump_sum_hours', models.DecimalField(null=True, verbose_name=b'Total Hours', max_digits=8, decimal_places=2, blank=True)),
                ('biweekly_pay', models.DecimalField(max_digits=8, decimal_places=2)),
                ('pay_periods', models.DecimalField(max_digits=6, decimal_places=1)),
                ('hourly_pay', models.DecimalField(max_digits=8, decimal_places=2)),
                ('hours', models.DecimalField(verbose_name=b'Biweekly Hours', max_digits=5, decimal_places=2)),
                ('reappointment', models.BooleanField(default=False, help_text=b'Are we re-appointing to the same position?')),
                ('medical_benefits', models.BooleanField(default=False, help_text=b'50% of Medical Service Plan')),
                ('dental_benefits', models.BooleanField(default=False, help_text=b'50% of Dental Plan')),
                ('notes', models.TextField(help_text=b'Biweekly emplyment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.', blank=True)),
                ('comments', models.TextField(help_text=b'For internal use', blank=True)),
                ('offer_letter_text', models.TextField(help_text=b'Text of the offer letter to be signed by the RA and supervisor.', null=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('deleted', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('account', models.ForeignKey(to='ra.Account')),
                ('hiring_faculty', models.ForeignKey(related_name='ra_hiring_faculty', to='coredata.Person', help_text=b'The manager who is hiring the RA.')),
                ('person', models.ForeignKey(related_name='ra_person', to='coredata.Person', help_text=b'The RA who is being appointed.')),
                ('project', models.ForeignKey(to='ra.Project')),
                ('scholarship', models.ForeignKey(blank=True, to='grad.Scholarship', help_text=b'Scholarship associated with this appointment. Optional.', null=True)),
                ('unit', models.ForeignKey(help_text=b'The unit that owns the appointment', to='coredata.Unit')),
            ],
            options={
                'ordering': ['person', 'created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SemesterConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('semester', models.ForeignKey(to='coredata.Semester')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='semesterconfig',
            unique_together=set([('unit', 'semester')]),
        ),
    ]
