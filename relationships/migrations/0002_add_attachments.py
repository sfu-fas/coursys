# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-22 12:48


import autoslug.fields
import datetime
import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion
import relationships.handlers
import relationships.models


class Migration(migrations.Migration):

    dependencies = [
        ('relationships', '0001_create_contacts_and_events'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', autoslug.fields.AutoSlugField(editable=False, populate_from='mediatype', unique_with=('event',))),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(max_length=500, storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=relationships.models.attachment_upload_to)),
                ('mediatype', models.CharField(blank=True, editable=False, max_length=200, null=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.RemoveField(
            model_name='event',
            name='attachment',
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.CharField(choices=[('quote', relationships.handlers.QuoteEvent), ('photo', relationships.handlers.PhotoEvent), ('employer', relationships.handlers.EmployerEvent)], max_length=10),
        ),
        migrations.AlterField(
            model_name='event',
            name='timestamp',
            field=models.DateTimeField(default=datetime.datetime.now, editable=False),
        ),
        migrations.AddField(
            model_name='eventattachment',
            name='event',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='relationships.Event'),
        ),
        migrations.AlterUniqueTogether(
            name='eventattachment',
            unique_together=set([('event', 'slug')]),
        ),
    ]
