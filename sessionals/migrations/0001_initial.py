# -*- coding: utf-8 -*-


from django.db import migrations, models
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionalAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60)),
                ('account_number', models.CharField(max_length=40)),
                ('position_number', models.PositiveIntegerField()),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='SessionalConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('appointment_start', models.DateField()),
                ('appointment_end', models.DateField()),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('unit', models.OneToOneField(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='SessionalContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sin', models.CharField(help_text=b'Social Insurance Number - 000000000 if unknown', max_length=30, verbose_name=b'SIN')),
                ('visa_verified', models.BooleanField(default=False, help_text=b"I have verified this sessional's visa information")),
                ('appointment_start', models.DateField()),
                ('appointment_end', models.DateField()),
                ('pay_start', models.DateField()),
                ('pay_end', models.DateField()),
                ('appt_guarantee', models.CharField(default=b'GUAR', max_length=4, verbose_name=b'Appoinment Guarantee', choices=[(b'GUAR', b'Appointment Guaranteed'), (b'COND', b'Appointment Conditional Upon Enrolment')])),
                ('appt_type', models.CharField(default=b'INIT', max_length=4, verbose_name=b'Appointment Type', choices=[(b'INIT', b'Initial Appointment to this Position Number'), (b'REAP', b'Reappointment to Same Position Number or Revision')])),
                ('contact_hours', models.DecimalField(verbose_name=b'Weekly Contact Hours', max_digits=6, decimal_places=2)),
                ('total_salary', models.DecimalField(max_digits=8, decimal_places=2)),
                ('notes', models.CharField(max_length=400, null=True, blank=True)),
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
