# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-18 17:09
from __future__ import unicode_literals

import autoslug.fields
import courselib.json_fields
from django.db import migrations, models
import django.db.models.deletion
import outreach.models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0008_add_dob_reg_cap_and_registration_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outreachevent',
            name='closed',
            field=models.BooleanField(default=False, help_text='If this box is checked, people will not be able to register for this event even if it is still current.', verbose_name='Close Registration'),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Cost of this event', max_digits=8, null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='email',
            field=models.EmailField(blank=True, help_text='Contact email.  Address that will be given to registrants on the registration success page in case they have any questions/problems.', max_length=254, null=True, verbose_name='Contact e-mail'),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='end_date',
            field=models.DateTimeField(help_text='Event end date and time', verbose_name='End Date and Time'),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='notes',
            field=models.CharField(blank=True, help_text='Special notes to registrants.  These *will* be displayed on the registration forms.', max_length=400, null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='registration_cap',
            field=models.PositiveIntegerField(blank=True, help_text='If you set a registration cap, people will not be allowed to register after you have reached this many registrations marked as attending.', null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='registration_email_text',
            field=models.TextField(blank=True, help_text='If you fill this in, this will be sent as an email to all all new registrants as a registration confirmation.', null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='resources',
            field=models.CharField(blank=True, help_text='Resources needed for this event.', max_length=400, null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='score',
            field=models.DecimalField(blank=True, decimal_places=0, help_text='The score according to the event score matrix', max_digits=2, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='autoslug', unique=True),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='start_date',
            field=models.DateTimeField(default=outreach.models.timezone_today, help_text='Event start date and time.  Use 24h format for the time if needed.', verbose_name='Start Date and Time'),
        ),
        migrations.AlterField(
            model_name='outreachevent',
            name='unit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='coredata.Unit'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='age',
            field=models.DecimalField(blank=True, decimal_places=0, max_digits=2, null=True, verbose_name='Participant Age'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='birthdate',
            field=models.DateField(verbose_name='Participant Date of Birth'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='config',
            field=courselib.json_fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Contact E-mail'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='outreach.OutreachEvent'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='first_name',
            field=models.CharField(max_length=32, verbose_name='Participant First Name'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='grade',
            field=models.PositiveSmallIntegerField(verbose_name='Participant Grade'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='last_name',
            field=models.CharField(max_length=32, verbose_name='Participant Last Name'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='middle_name',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Participant Middle Name'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='notes',
            field=models.CharField(blank=True, max_length=400, null=True, verbose_name='Allergies/Dietary Restrictions'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='participation_waiver',
            field=models.BooleanField(default=False, help_text='Check this box if you agree with the participation waiver.', verbose_name="I, the parent or guardian of the Child, agree to HOLD HARMLESS AND INDEMNIFY the FAS Outreach Program and SFU for any and all liability to which the University has no legal obligation, including but not limited to, any damage to the property of, or personal injury to my child or for injury and/or property damage suffered by any third party resulting from my child's actions whilst participating in the program. By signing this consent, I agree to allow SFU staff to provide or cause to be provided such medical services as the University or medical personnel consider appropriate. The FAS Outreach Program reserves the right to refuse further participation to any participant for rule infractions."),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='photo_waiver',
            field=models.BooleanField(default=False, help_text='Check this box if you agree with the photo waiver.', verbose_name='I, the parent or guardian of the Child, hereby authorize the Faculty of Applied Sciences (FAS) Outreach program of Simon Fraser University to photograph, audio record, video record, podcast and/or webcast the Child (digitally or otherwise) without charge; and to allow the FAS Outreach Program to copy, modify and distribute in print and online, those images that include my child in whatever appropriate way either the FAS Outreach Program and/or SFU sees fit without having to seek further approval. No names will be used in association with any images or recordings.'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='previously_attended',
            field=models.BooleanField(default=False, help_text='Check here if you have attended this event in the past', verbose_name='I have previously attended this event'),
        ),
        migrations.AlterField(
            model_name='outreacheventregistration',
            name='school',
            field=models.CharField(max_length=200, verbose_name='Participant School'),
        ),
    ]
