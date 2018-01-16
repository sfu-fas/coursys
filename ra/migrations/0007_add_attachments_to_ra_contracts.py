# -*- coding: utf-8 -*-


from django.db import migrations, models
import autoslug.fields
import django.core.files.storage
import ra.models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
        ('ra', '0006_auto_20160823_1238'),
    ]

    operations = [
        migrations.CreateModel(
            name='RAAppointmentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', unique_with=(b'appointment',), editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=ra.models.ra_attachment_upload_to)),
                ('mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('appointment', models.ForeignKey(related_name='attachments', to='ra.RAAppointment')),
                ('created_by', models.ForeignKey(help_text=b'Document attachment created by.', to='coredata.Person')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AlterUniqueTogether(
            name='raappointmentattachment',
            unique_together=set([('appointment', 'slug')]),
        ),
    ]
