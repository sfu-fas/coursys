# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import datetime
from decimal import Decimal
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        ('ra', '0001_initial'),
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailReceipt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.ForeignKey(editable=False, to='dashboard.NewsItem')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HiringSemester',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deadline_for_acceptance', models.DateField()),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('payperiods', models.DecimalField(verbose_name=b'During the contract, how many bi-weekly pay periods?', max_digits=4, decimal_places=2)),
                ('config', courselib.json_fields.JSONField(default={}, editable=False)),
                ('semester', models.ForeignKey(to='coredata.Semester')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TACategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(help_text=b"Category Choice Code - for example 'GTA2'", max_length=5)),
                ('title', models.CharField(help_text=b"Category Choice Title - for example 'PhD'", max_length=50)),
                ('pay_per_bu', models.DecimalField(verbose_name=b'Default pay, per base unit', max_digits=8, decimal_places=2)),
                ('scholarship_per_bu', models.DecimalField(verbose_name=b'Scholarship pay, per base unit', max_digits=8, decimal_places=2)),
                ('bu_lab_bonus', models.DecimalField(default=Decimal('0.17'), verbose_name=b'Bonus BUs awarded to a course with a lab', max_digits=8, decimal_places=2)),
                ('hours_per_bu', models.DecimalField(default=Decimal('42'), verbose_name=b'Hours per BU', max_digits=6, decimal_places=2)),
                ('holiday_hours_per_bu', models.DecimalField(default=Decimal('1.1'), verbose_name=b'Holiday hours per BU', max_digits=4, decimal_places=2)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('created', models.DateTimeField(default=datetime.datetime(2014, 12, 21, 15, 39, 54, 818244), editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('config', courselib.json_fields.JSONField(default={}, editable=False)),
                ('account', models.ForeignKey(to='ra.Account')),
                ('hiring_semester', models.ForeignKey(editable=False, to='tacontracts.HiringSemester')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TAContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'NEW', max_length=4, editable=False, choices=[(b'NEW', b'Draft'), (b'SGN', b'Signed'), (b'CAN', b'Cancelled')])),
                ('sin', models.CharField(help_text=b'Social Insurance Number - 000000000 if unknown', max_length=30, verbose_name=b'SIN')),
                ('deadline_for_acceptance', models.DateField()),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('payperiods', models.DecimalField(verbose_name=b'During the contract, how many bi-weekly pay periods?', max_digits=4, decimal_places=2)),
                ('appointment', models.CharField(default=b'INIT', max_length=4, choices=[(b'INIT', b'Initial appointment to this position'), (b'REAP', b'Reappointment to same position or revision to appointment')])),
                ('conditional_appointment', models.BooleanField(default=False)),
                ('tssu_appointment', models.BooleanField(default=True)),
                ('accepted_by_student', models.BooleanField(default=False, help_text=b'Has the student accepted the contract?')),
                ('comments', models.TextField(blank=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.CharField(max_length=20, editable=False)),
                ('config', courselib.json_fields.JSONField(default={}, editable=False)),
                ('category', models.ForeignKey(related_name='contract', to='tacontracts.TACategory')),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TACourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bu', models.DecimalField(help_text=b'The number of Base Units for this course.', verbose_name=b'BUs', max_digits=4, decimal_places=2)),
                ('labtut', models.BooleanField(default=False, help_text=b'Does this course have a lab or tutorial?', verbose_name=b'Lab/Tutorial?')),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('config', courselib.json_fields.JSONField(default={}, editable=False)),
                ('contract', models.ForeignKey(related_name='course', editable=False, to='tacontracts.TAContract')),
                ('course', models.ForeignKey(related_name='+', to='coredata.CourseOffering')),
                ('member', models.ForeignKey(related_name='tacourse', editable=False, to='coredata.Member', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tacourse',
            unique_together=set([('contract', 'course')]),
        ),
        migrations.AlterUniqueTogether(
            name='hiringsemester',
            unique_together=set([('semester', 'unit')]),
        ),
        migrations.AddField(
            model_name='emailreceipt',
            name='contract',
            field=models.ForeignKey(related_name='email_receipt', editable=False, to='tacontracts.TAContract'),
            preserve_default=True,
        ),
    ]
